from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.messages.middleware import MessageMiddleware
from django.http import Http404, HttpResponseForbidden, HttpResponse
from django.test import RequestFactory, TestCase

from banking import views
from banking.models import Account, ActivityLog, Transaction, UserProfile
from banking.services import BankingError


def _attach_session_and_messages(request):
    # instantiate middlewares with a dummy get_response callable (required by Django middleware API)
    SessionMiddleware(get_response=lambda req: None).process_request(request)
    request.session.save()
    MessageMiddleware(get_response=lambda req: None).process_request(request)
    request.session.save()


def _fake_render(request, template_name, context=None, *args, **kwargs):
    resp = HttpResponse(f"rendered:{template_name}")
    resp.template_name = template_name
    resp.context = context or {}
    return resp


def _fake_redirect(*args, **kwargs):
    # return an HttpResponse that encodes the redirect target for assertions
    return HttpResponse(f"redirected:{args[0] if args else ''}")


class ViewsTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username="tester", password="secret")
        # default profile is customer
        UserProfile.objects.create(user=self.user)
        self.admin = User.objects.create_user(username="admin", password="secret")
        UserProfile.objects.create(user=self.admin, role=UserProfile.ROLE_ADMIN)

        # create accounts for tester
        self.acc1 = Account.objects.create(
            owner=self.user,
            account_number="ACC1001",
            account_name="Tester Checking",
            account_type=Account.ACCOUNT_CHECKING,
            balance=Decimal("100.00"),
        )
        self.acc2 = Account.objects.create(
            owner=self.user,
            account_number="ACC1002",
            account_name="Tester Savings",
            account_type=Account.ACCOUNT_SAVINGS,
            balance=Decimal("50.00"),
        )

        # account for another user
        other = User.objects.create_user(username="other", password="x")
        self.other_acc = Account.objects.create(
            owner=other,
            account_number="ACC2001",
            account_name="Other Checking",
            account_type=Account.ACCOUNT_CHECKING,
            balance=Decimal("30.00"),
        )

    def test_login_view_get_when_authenticated_redirects_to_dashboard_or_admin(self):
        # customer user
        req = self.factory.get("/login/")
        req.user = self.user
        with patch.object(views, "redirect", side_effect=_fake_redirect) as mock_redirect:
            resp = views.login_view(req)
            self.assertEqual(resp.content.decode(), "redirected:dashboard")
            mock_redirect.assert_called_once()

        # admin user
        req2 = self.factory.get("/login/")
        req2.user = self.admin
        with patch.object(views, "redirect", side_effect=_fake_redirect) as mock_redirect2:
            resp2 = views.login_view(req2)
            self.assertEqual(resp2.content.decode(), "redirected:admin_dashboard")
            mock_redirect2.assert_called_once()

    def test_login_view_post_success_and_activity_logged(self):
        req = self.factory.post("/login/", {"username": "tester", "password": "secret"})
        req.user = type("U", (), {"is_authenticated": False})()  # anonymous-like for initial check
        _attach_session_and_messages(req)

        with patch.object(views, "redirect", side_effect=_fake_redirect) as mock_redirect:
            resp = views.login_view(req)
            # Should redirect to dashboard for normal user
            self.assertEqual(resp.content.decode(), "redirected:dashboard")
            mock_redirect.assert_called_once()

        # ActivityLog for login should have been created
        self.assertTrue(ActivityLog.objects.filter(user__username="tester", action_type=ActivityLog.ACTION_LOGIN).exists())

    def test_login_view_post_failed_creates_failed_login_log_and_message(self):
        req = self.factory.post("/login/", {"username": "nonexistent", "password": "bad"})
        req.user = type("U", (), {"is_authenticated": False})()
        _attach_session_and_messages(req)

        with patch.object(views, "render", side_effect=_fake_render) as mock_render:
            resp = views.login_view(req)
            # render called for login page on failure
            self.assertEqual(resp.template_name, "login.html")
            # failed login activity log created (user is None on the ActivityLog in the view)
            self.assertTrue(ActivityLog.objects.filter(action_type=ActivityLog.ACTION_FAILED_LOGIN).exists())
            mock_render.assert_called_once()

    def test_dashboard_view_renders_for_customer_and_redirects_for_admin(self):
        # customer
        req = self.factory.get("/dashboard/")
        req.user = self.user
        _attach_session_and_messages(req)
        with patch.object(views, "render", side_effect=_fake_render) as mock_render:
            resp = views.dashboard_view(req)
            self.assertEqual(resp.template_name, "dashboard.html")
            self.assertIn("accounts", resp.context)
            self.assertIn(self.acc1, list(resp.context["accounts"]))
            mock_render.assert_called_once()

        # admin should be redirected to admin_dashboard
        req2 = self.factory.get("/dashboard/")
        req2.user = self.admin
        _attach_session_and_messages(req2)
        with patch.object(views, "redirect", side_effect=_fake_redirect) as mock_redirect:
            resp2 = views.dashboard_view(req2)
            self.assertEqual(resp2.content.decode(), "redirected:admin_dashboard")
            mock_redirect.assert_called_once()

    def test_account_detail_view_owner_and_non_owner(self):
        # owner can view
        req = self.factory.get("/accounts/{}/".format(self.acc1.id))
        req.user = self.user
        _attach_session_and_messages(req)
        with patch.object(views, "render", side_effect=_fake_render) as mock_render:
            resp = views.account_detail_view(req, account_id=self.acc1.id)
            self.assertEqual(resp.template_name, "account_detail.html")
            self.assertEqual(resp.context["account"].id, self.acc1.id)

        # non-owner should raise Http404
        req2 = self.factory.get("/accounts/{}/".format(self.other_acc.id))
        req2.user = self.user
        _attach_session_and_messages(req2)
        with self.assertRaises(Http404):
            views.account_detail_view(req2, account_id=self.other_acc.id)

    def test_transfer_view_post_success_and_failure(self):
        req = self.factory.post("/transfer/", {"source_account_id": str(self.acc1.id), "destination_account_id": str(self.acc2.id), "amount": "10.00"})
        req.user = self.user
        _attach_session_and_messages(req)

        # success path: mock the service to succeed
        with patch.object(views, "transfer_between_accounts", return_value=MagicMock()) as mock_service, patch.object(views, "redirect", side_effect=_fake_redirect) as mock_redirect:
            resp = views.transfer_view(req)
            mock_service.assert_called_once()
            self.assertEqual(resp.content.decode(), "redirected:dashboard")

        # failure path: service raises BankingError -> should render transfer.html and set error message
        req2 = self.factory.post("/transfer/", {"source_account_id": str(self.acc1.id), "destination_account_id": str(self.acc2.id), "amount": "10000.00"})
        req2.user = self.user
        _attach_session_and_messages(req2)
        with patch.object(views, "transfer_between_accounts", side_effect=BankingError("Insufficient funds")), patch.object(views, "render", side_effect=_fake_render) as mock_render:
            resp2 = views.transfer_view(req2)
            self.assertEqual(resp2.template_name, "transfer.html")
            mock_render.assert_called_once()

    def test_admin_dashboard_requires_admin(self):
        # non-admin should get forbidden
        req = self.factory.get("/admin/")
        req.user = self.user
        _attach_session_and_messages(req)
        resp = views.admin_dashboard_view(req)
        self.assertIsInstance(resp, HttpResponseForbidden)

        # admin can view and receives expected context keys
        req2 = self.factory.get("/admin/")
        req2.user = self.admin
        _attach_session_and_messages(req2)
        with patch.object(views, "render", side_effect=_fake_render) as mock_render:
            resp2 = views.admin_dashboard_view(req2)
            self.assertEqual(resp2.template_name, "admin_dashboard.html")
            # ensure keys exist in context
            self.assertIn("accounts", resp2.context)
            self.assertIn("transactions", resp2.context)
            self.assertIn("logs", resp2.context)
            mock_render.assert_called_once()