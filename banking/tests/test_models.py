from decimal import Decimal

from django.contrib.auth.models import User
from django.db import IntegrityError
from django.test import TestCase

from banking.models import Account, ActivityLog, Transaction, UserProfile


class ModelsTestCase(TestCase):
    def setUp(self):
        # Users
        self.user1 = User.objects.create_user(username="alice", password="password")
        self.user2 = User.objects.create_user(username="bob", password="password")

        # Profiles (OneToOne)
        self.profile1 = UserProfile.objects.create(user=self.user1)
        self.profile2 = UserProfile.objects.create(user=self.user2, role=UserProfile.ROLE_ADMIN)

        # Accounts
        self.account1 = Account.objects.create(
            owner=self.user1,
            account_number="ACC1001",
            account_name="Alice Checking",
            account_type=Account.ACCOUNT_CHECKING,
        )
        self.account2 = Account.objects.create(
            owner=self.user2,
            account_number="ACC2001",
            account_name="Bob Savings",
            account_type=Account.ACCOUNT_SAVINGS,
            balance=Decimal("150.00"),
        )

        # Transaction examples
        self.deposit = Transaction.objects.create(
            account=self.account1,
            transaction_type=Transaction.TYPE_DEPOSIT,
            amount=Decimal("50.00"),
            description="Initial deposit",
        )

        self.transfer_out = Transaction.objects.create(
            account=self.account1,
            transaction_type=Transaction.TYPE_TRANSFER_OUT,
            amount=Decimal("25.00"),
            source_account=self.account1,
            destination_account=self.account2,
            description="Transfer to Bob",
        )

        # Activity log
        self.activity = ActivityLog.objects.create(
            user=self.user1,
            action_type=ActivityLog.ACTION_DEPOSIT,
            details="Deposited funds",
        )

    def test_userprofile_defaults_and_str(self):
        assert self.profile1.role == UserProfile.ROLE_CUSTOMER
        assert str(self.profile1) == f"{self.user1.username} ({self.profile1.role})"

        assert self.profile2.role == UserProfile.ROLE_ADMIN
        assert "bob" in str(self.profile2)

    def test_account_defaults_and_str(self):
        # default balance is 0.00 for account1
        assert self.account1.balance == Decimal("0.00")
        assert str(self.account1) == f"{self.account1.account_name} - {self.account1.account_number}"

        # explicit balance preserved
        assert self.account2.balance == Decimal("150.00")

    def test_account_unique_account_number_enforced(self):
        with self.assertRaises(IntegrityError):
            # attempt to create another account with same account_number as account1
            Account.objects.create(
                owner=self.user2,
                account_number=self.account1.account_number,
                account_name="Duplicate",
                account_type=Account.ACCOUNT_CHECKING,
            )

    def test_transaction_str_and_relations(self):
        assert self.deposit.transaction_type == Transaction.TYPE_DEPOSIT
        assert "deposit" in str(self.deposit)
        assert f"${self.deposit.amount}" in str(self.deposit)

        # transfer relationships set correctly
        assert self.transfer_out.source_account == self.account1
        assert self.transfer_out.destination_account == self.account2
        # related_name accessors
        assert self.transfer_out in list(self.account1.outgoing_transfer_transactions.all())
        assert self.transfer_out in list(self.account2.incoming_transfer_transactions.all())

    def test_activitylog_str_and_ordering(self):
        s = str(self.activity)
        assert ActivityLog.ACTION_DEPOSIT in s
        assert self.activity in list(ActivityLog.objects.all())

    def test_cascade_delete_user_removes_accounts(self):
        # deleting user1 should delete account1 (on_delete=CASCADE)
        self.user1.delete()
        assert not Account.objects.filter(account_number=self.account1.account_number).exists()