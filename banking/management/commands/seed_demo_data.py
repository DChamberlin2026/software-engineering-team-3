from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from banking.models import Account, ActivityLog, Transaction, UserProfile


class Command(BaseCommand):
    help = "Creates demo users, accounts, transactions, and activity logs for SEBS."

    def handle(self, *args, **options):
        self.stdout.write("Seeding demo data...")

        admin_user, _ = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@example.com",
                "first_name": "Admin",
                "last_name": "User",
            },
        )
        admin_user.set_password("admin123")
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.save()

        UserProfile.objects.update_or_create(
            user=admin_user,
            defaults={"role": UserProfile.ROLE_ADMIN},
        )

        customer_user, _ = User.objects.get_or_create(
            username="customer1",
            defaults={
                "email": "customer1@example.com",
                "first_name": "Demo",
                "last_name": "Customer",
            },
        )
        customer_user.set_password("password123")
        customer_user.save()

        UserProfile.objects.update_or_create(
            user=customer_user,
            defaults={"role": UserProfile.ROLE_CUSTOMER},
        )

        checking, _ = Account.objects.update_or_create(
            account_number="100001",
            defaults={
                "owner": customer_user,
                "account_name": "Demo Checking",
                "account_type": Account.ACCOUNT_CHECKING,
                "balance": Decimal("1250.00"),
            },
        )

        savings, _ = Account.objects.update_or_create(
            account_number="100002",
            defaults={
                "owner": customer_user,
                "account_name": "Demo Savings",
                "account_type": Account.ACCOUNT_SAVINGS,
                "balance": Decimal("3000.00"),
            },
        )

        Transaction.objects.filter(account__owner=customer_user).delete()

        Transaction.objects.create(
            account=checking,
            transaction_type=Transaction.TYPE_DEPOSIT,
            amount=Decimal("500.00"),
            destination_account=checking,
            description="Initial demo deposit",
        )

        Transaction.objects.create(
            account=checking,
            transaction_type=Transaction.TYPE_WITHDRAWAL,
            amount=Decimal("75.00"),
            source_account=checking,
            description="Demo withdrawal",
        )

        Transaction.objects.create(
            account=checking,
            transaction_type=Transaction.TYPE_TRANSFER_OUT,
            amount=Decimal("100.00"),
            source_account=checking,
            destination_account=savings,
            description="Demo transfer out",
        )

        Transaction.objects.create(
            account=savings,
            transaction_type=Transaction.TYPE_TRANSFER_IN,
            amount=Decimal("100.00"),
            source_account=checking,
            destination_account=savings,
            description="Demo transfer in",
        )

        ActivityLog.objects.get_or_create(
            user=admin_user,
            action_type=ActivityLog.ACTION_ACCOUNT_CREATED,
            details="Demo data created for local development.",
        )

        ActivityLog.objects.get_or_create(
            user=customer_user,
            action_type=ActivityLog.ACTION_DEPOSIT,
            details="Initial demo deposit created.",
        )

        self.stdout.write(self.style.SUCCESS("Demo data seeded successfully."))
        self.stdout.write("Admin login: admin / admin123")
        self.stdout.write("Customer login: customer1 / password123")