from django.contrib import admin
from django.urls import path

from banking import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.login_view, name="login"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("accounts/<int:account_id>/", views.account_detail_view, name="account_detail"),
    path("deposit/", views.deposit_view, name="deposit"),
    path("deposit/<int:account_id>/", views.deposit_view, name="deposit"),
    path("withdrawal/", views.withdrawal_view, name="withdrawal"),
    path("withdraw/<int:account_id>/", views.withdrawal_view, name="withdraw"),
    path("transfer/", views.transfer_view, name="transfer"),
    path("history/", views.transaction_history_view, name="transaction_history"),
    path("admin-dashboard/", views.admin_dashboard_view, name="admin_dashboard"),
    path("admin-dashboard/accounts/<int:account_id>/", views.admin_manage_account_view, name="admin_manage_account"),
]
