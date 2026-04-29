from decimal import Decimal

from django.contrib.auth.models import User
from django.db import models


class UserProfile(models.Model):
    ROLE_CUSTOMER = "customer"
    ROLE_ADMIN = "administrator"

    ROLE_CHOICES = [
        (ROLE_CUSTOMER, "Customer"),
        (ROLE_ADMIN, "Administrator"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_CUSTOMER)

    def __str__(self):
        return f"{self.user.username} ({self.role})"


class Account(models.Model):
    ACCOUNT_CHECKING = "checking"
    ACCOUNT_SAVINGS = "savings"

    ACCOUNT_TYPE_CHOICES = [
        (ACCOUNT_CHECKING, "Checking"),
        (ACCOUNT_SAVINGS, "Savings"),
    ]

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="accounts")
    account_number = models.CharField(max_length=20, unique=True)
    account_name = models.CharField(max_length=100)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPE_CHOICES)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["account_number"]

    def __str__(self):
        return f"{self.account_name} - {self.account_number}"


class Transaction(models.Model):
    TYPE_DEPOSIT = "deposit"
    TYPE_WITHDRAWAL = "withdrawal"
    TYPE_TRANSFER_IN = "transfer_in"
    TYPE_TRANSFER_OUT = "transfer_out"

    TRANSACTION_TYPE_CHOICES = [
        (TYPE_DEPOSIT, "Deposit"),
        (TYPE_WITHDRAWAL, "Withdrawal"),
        (TYPE_TRANSFER_IN, "Transfer In"),
        (TYPE_TRANSFER_OUT, "Transfer Out"),
    ]

    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="transactions")
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_date = models.DateTimeField(auto_now_add=True)

    source_account = models.ForeignKey(
        Account,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="outgoing_transfer_transactions",
    )

    destination_account = models.ForeignKey(
        Account,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="incoming_transfer_transactions",
    )

    description = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-transaction_date"]

    def __str__(self):
        return f"{self.transaction_type} - ${self.amount}"


class ActivityLog(models.Model):
    ACTION_LOGIN = "login"
    ACTION_FAILED_LOGIN = "failed_login"
    ACTION_LOGOUT = "logout"
    ACTION_DEPOSIT = "deposit"
    ACTION_WITHDRAWAL = "withdrawal"
    ACTION_TRANSFER = "transfer"
    ACTION_ACCOUNT_CREATED = "account_created"
    ACTION_ACCOUNT_UPDATED = "account_updated"

    ACTION_TYPE_CHOICES = [
        (ACTION_LOGIN, "Login"),
        (ACTION_FAILED_LOGIN, "Failed Login"),
        (ACTION_LOGOUT, "Logout"),
        (ACTION_DEPOSIT, "Deposit"),
        (ACTION_WITHDRAWAL, "Withdrawal"),
        (ACTION_TRANSFER, "Transfer"),
        (ACTION_ACCOUNT_CREATED, "Account Created"),
        (ACTION_ACCOUNT_UPDATED, "Account Updated"),
    ]

    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    action_type = models.CharField(max_length=50, choices=ACTION_TYPE_CHOICES)
    action_datetime = models.DateTimeField(auto_now_add=True)
    details = models.TextField(blank=True)

    class Meta:
        ordering = ["-action_datetime"]

    def __str__(self):
        return f"{self.action_type} - {self.action_datetime}"