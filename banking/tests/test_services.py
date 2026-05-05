from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from banking import services
from banking.models import Account, Transaction, ActivityLog


class ServicesTestCase(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username="user1", password="pass")
        self.user2 = User.objects.create_user(username="user2", password="pass")

        self.acc1 = Account.objects.create(
            owner=self.user1,
            account_number="ACC1001",
            account_name="User1 Checking",
            account_type=Account.ACCOUNT_CHECKING,
            balance=Decimal("100.00"),
        )

        self.acc2 = Account.objects.create(
            owner=self.user1,
            account_number="ACC1002",
            account_name="User1 Savings",
            account_type=Account.ACCOUNT_SAVINGS,
            balance=Decimal("50.00"),
        )

        self.other_acc = Account.objects.create(
            owner=self.user2,
            account_number="ACC2001",
            account_name="User2 Checking",
            account_type=Account.ACCOUNT_CHECKING,
            balance=Decimal("30.00"),
        )

    def test_deposit_updates_balance_and_creates_transaction_and_activity(self):
        prev_balance = self.acc1.balance
        amount = Decimal("25.50")

        txn = services.deposit_to_account(self.user1, self.acc1.id, amount)

        self.acc1.refresh_from_db()
        self.assertEqual(self.acc1.balance, prev_balance + amount)

        self.assertIsInstance(txn, Transaction)
        self.assertEqual(txn.transaction_type, Transaction.TYPE_DEPOSIT)
        self.assertEqual(txn.amount, amount)
        self.assertEqual(txn.destination_account_id, self.acc1.id)

        self.assertTrue(
            ActivityLog.objects.filter(user=self.user1, action_type=ActivityLog.ACTION_DEPOSIT).exists()
        )

    def test_deposit_invalid_amount_raises(self):
        with self.assertRaises(services.BankingError):
            services.deposit_to_account(self.user1, self.acc1.id, "-10")

        with self.assertRaises(services.BankingError):
            services.deposit_to_account(self.user1, self.acc1.id, "not-a-number")

    def test_withdraw_updates_balance_and_creates_transaction_and_activity(self):
        prev_balance = self.acc1.balance
        amount = Decimal("40.00")

        txn = services.withdraw_from_account(self.user1, self.acc1.id, amount)

        self.acc1.refresh_from_db()
        self.assertEqual(self.acc1.balance, prev_balance - amount)

        self.assertIsInstance(txn, Transaction)
        self.assertEqual(txn.transaction_type, Transaction.TYPE_WITHDRAWAL)
        self.assertEqual(txn.amount, amount)
        self.assertEqual(txn.source_account_id, self.acc1.id)

        self.assertTrue(
            ActivityLog.objects.filter(user=self.user1, action_type=ActivityLog.ACTION_WITHDRAWAL).exists()
        )

    def test_withdraw_insufficient_funds_raises(self):
        with self.assertRaises(services.BankingError):
            services.withdraw_from_account(self.user1, self.acc1.id, Decimal("1000.00"))

    def test_withdraw_access_denied_raises(self):
        # user1 attempting to withdraw from user2's account
        with self.assertRaises(services.BankingError):
            services.withdraw_from_account(self.user1, self.other_acc.id, Decimal("1.00"))

    def test_transfer_between_accounts_updates_balances_and_creates_transactions_and_activity(self):
        src_prev = self.acc1.balance
        dst_prev = self.acc2.balance
        amount = Decimal("60.00")

        txn_out = services.transfer_between_accounts(self.user1, self.acc1.id, self.acc2.id, amount)

        self.acc1.refresh_from_db()
        self.acc2.refresh_from_db()

        self.assertEqual(self.acc1.balance, src_prev - amount)
        self.assertEqual(self.acc2.balance, dst_prev + amount)

        self.assertIsInstance(txn_out, Transaction)
        self.assertEqual(txn_out.transaction_type, Transaction.TYPE_TRANSFER_OUT)
        self.assertEqual(txn_out.amount, amount)
        self.assertEqual(txn_out.source_account_id, self.acc1.id)
        self.assertEqual(txn_out.destination_account_id, self.acc2.id)

        # Check corresponding transfer in transaction exists
        self.assertTrue(
            Transaction.objects.filter(
                account=self.acc2, transaction_type=Transaction.TYPE_TRANSFER_IN, amount=amount
            ).exists()
        )

        self.assertTrue(
            ActivityLog.objects.filter(user=self.user1, action_type=ActivityLog.ACTION_TRANSFER).exists()
        )

    def test_transfer_insufficient_funds_raises(self):
        with self.assertRaises(services.BankingError):
            services.transfer_between_accounts(self.user1, self.acc1.id, self.acc2.id, Decimal("1000.00"))

    def test_transfer_same_account_raises(self):
        with self.assertRaises(services.BankingError):
            services.transfer_between_accounts(self.user1, self.acc1.id, self.acc1.id, Decimal("1.00"))

    def test_operations_on_other_users_account_raise_access_denied(self):
        with self.assertRaises(services.BankingError):
            services.deposit_to_account(self.user1, self.other_acc.id, Decimal("5.00"))

        with self.assertRaises(services.BankingError):
            services.withdraw_from_account(self.user1, self.other_acc.id, Decimal("5.00"))


class ServiceEquivalencePartitionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u", password="p")
        self.other = User.objects.create_user(username="other", password="p")
        self.acc_a = Account.objects.create(
            owner=self.user,
            account_number="P1001",
            account_name="A",
            account_type=Account.ACCOUNT_CHECKING,
            balance=Decimal("100.00"),
        )
        self.acc_b = Account.objects.create(
            owner=self.user,
            account_number="P1002",
            account_name="B",
            account_type=Account.ACCOUNT_SAVINGS,
            balance=Decimal("10.00"),
        )
        self.other_acc = Account.objects.create(
            owner=self.other,
            account_number="P2001",
            account_name="Other",
            account_type=Account.ACCOUNT_CHECKING,
            balance=Decimal("50.00"),
        )

    def test_non_numeric_amount_raises(self):
        with self.assertRaises(services.BankingError):
            services.transfer_between_accounts(self.user, self.acc_a.id, self.acc_b.id, "abc")

    def test_zero_and_negative_amounts_raise(self):
        with self.assertRaises(services.BankingError):
            services.transfer_between_accounts(self.user, self.acc_a.id, self.acc_b.id, "0")
        with self.assertRaises(services.BankingError):
            services.transfer_between_accounts(self.user, self.acc_a.id, self.acc_b.id, "-5.00")

    def test_transfer_exact_balance_succeeds(self):
        services.transfer_between_accounts(self.user, self.acc_a.id, self.acc_b.id, "100.00")
        self.acc_a.refresh_from_db()
        self.acc_b.refresh_from_db()
        self.assertEqual(self.acc_a.balance, Decimal("0.00"))
        self.assertEqual(self.acc_b.balance, Decimal("110.00"))

    def test_transfer_to_other_user_account_succeeds(self):
        """
        Ensure payments can be made to accounts owned by other users.
        The service is expected to allow a user to transfer out from their account
        to any existing destination account (owned by another user).
        """
        src_prev = self.acc_a.balance
        dst_prev = self.other_acc.balance
        amount = Decimal("25.00")

        txn_out = services.transfer_between_accounts(self.user, self.acc_a.id, self.other_acc.id, amount)

        self.acc_a.refresh_from_db()
        self.other_acc.refresh_from_db()

        # balances updated on both accounts
        self.assertEqual(self.acc_a.balance, src_prev - amount)
        self.assertEqual(self.other_acc.balance, dst_prev + amount)

        # transfer out transaction created and points to destination
        self.assertIsInstance(txn_out, Transaction)
        self.assertEqual(txn_out.transaction_type, Transaction.TYPE_TRANSFER_OUT)
        self.assertEqual(txn_out.amount, amount)
        self.assertEqual(txn_out.source_account_id, self.acc_a.id)
        self.assertEqual(txn_out.destination_account_id, self.other_acc.id)

        # verify corresponding transfer-in exists on destination account
        self.assertTrue(
            Transaction.objects.filter(
                account=self.other_acc, transaction_type=Transaction.TYPE_TRANSFER_IN, amount=amount
            ).exists()
        )

        # activity log recorded for initiating user
        self.assertTrue(
            ActivityLog.objects.filter(user=self.user, action_type=ActivityLog.ACTION_TRANSFER).exists()
        )

    def test_nonexistent_account_id_raises(self):
        with self.assertRaises(services.BankingError):
            services.transfer_between_accounts(self.user, 999999, self.acc_b.id, "1.00")
