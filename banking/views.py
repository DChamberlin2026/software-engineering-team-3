from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .models import Account, ActivityLog, Transaction
from .services import BankingError, deposit_to_account, transfer_between_accounts, withdraw_from_account


def _is_admin(user):
    return hasattr(user, "profile") and user.profile.role == "administrator"


@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect("admin_dashboard" if _is_admin(request.user) else "dashboard")
    if request.method == "POST":
        user = authenticate(request, username=request.POST.get("username", ""), password=request.POST.get("password", ""))
        if user:
            login(request, user)
            ActivityLog.objects.create(user=user, action_type=ActivityLog.ACTION_LOGIN, details="User logged in")
            return redirect("admin_dashboard" if _is_admin(user) else "dashboard")
        ActivityLog.objects.create(action_type=ActivityLog.ACTION_FAILED_LOGIN, details=f"Failed login for {request.POST.get('username','')}")
        messages.error(request, "Invalid username or password.")
    return render(request, "login.html")


@require_POST
def logout_view(request):
    if request.user.is_authenticated:
        ActivityLog.objects.create(user=request.user, action_type=ActivityLog.ACTION_LOGOUT, details="User logged out")
    logout(request)
    return redirect("login")


@login_required
@require_GET
def dashboard_view(request):
    if _is_admin(request.user):
        return redirect("admin_dashboard")
    accounts = Account.objects.filter(owner=request.user)
    transactions = Transaction.objects.filter(account__owner=request.user).select_related("account")[:10]
    return render(request, "dashboard.html", {"accounts": accounts, "transactions": transactions})


@login_required
@require_GET
def account_detail_view(request, account_id):
    account = get_object_or_404(Account, id=account_id, owner=request.user)
    transactions = account.transactions.all()[:20]
    return render(request, "account_detail.html", {"account": account, "transactions": transactions})


@login_required
@require_http_methods(["GET", "POST"])
def transfer_view(request):
    accounts = Account.objects.filter(owner=request.user)
    if request.method == "POST":
        try:
            transfer_between_accounts(request.user, int(request.POST.get("source_account_id")), int(request.POST.get("destination_account_id")), request.POST.get("amount"))
            messages.success(request, "Transfer completed successfully.")
            return redirect("dashboard")
        except (BankingError, TypeError, ValueError) as exc:
            messages.error(request, str(exc))
    return render(request, "transfer.html", {"accounts": accounts})


@login_required
@require_http_methods(["GET", "POST"])
def withdrawal_view(request, account_id=None):
    accounts = Account.objects.filter(owner=request.user)
    if request.method == "POST":
        try:
            selected = int(request.POST.get("account_id") or account_id)
            withdraw_from_account(request.user, selected, request.POST.get("amount"))
            messages.success(request, "Withdrawal completed successfully.")
            return redirect("dashboard")
        except (BankingError, TypeError, ValueError) as exc:
            messages.error(request, str(exc))
    return render(request, "withdrawal.html", {"accounts": accounts, "selected_account": account_id})


@login_required
@require_http_methods(["GET", "POST"])
def deposit_view(request, account_id=None):
    accounts = Account.objects.filter(owner=request.user)
    if request.method == "POST":
        try:
            selected = int(request.POST.get("account_id") or account_id)
            deposit_to_account(request.user, selected, request.POST.get("amount"))
            messages.success(request, "Deposit completed successfully.")
            return redirect("dashboard")
        except (BankingError, TypeError, ValueError) as exc:
            messages.error(request, str(exc))
    return render(request, "deposit.html", {"accounts": accounts, "selected_account": account_id})


@login_required
@require_GET
def transaction_history_view(request):
    transactions = Transaction.objects.filter(account__owner=request.user).select_related("account")[:100]
    return render(request, "transaction_history.html", {"transactions": transactions})


@login_required
@require_GET
def admin_dashboard_view(request):
    if not _is_admin(request.user):
        return HttpResponseForbidden("Admins only")
    return render(
        request,
        "admin_dashboard.html",
        {
            "accounts": Account.objects.select_related("owner")[:200],
            "transactions": Transaction.objects.select_related("account", "account__owner")[:200],
            "logs": ActivityLog.objects.select_related("user")[:200],
        },
    )


@login_required
@require_GET
def admin_manage_account_view(request, account_id):
    if not _is_admin(request.user):
        return HttpResponseForbidden("Admins only")
    account = get_object_or_404(Account.objects.select_related("owner"), id=account_id)
    transactions = account.transactions.all()[:50]
    return render(request, "account_detail.html", {"account": account, "transactions": transactions})
