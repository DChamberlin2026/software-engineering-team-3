from decimal import Decimal, InvalidOperation

from django.db import transaction

from .models import Account, ActivityLog, Transaction


class BankingError(Exception):
    pass


def _clean_amount(amount):
    try:
        amount = Decimal(str(amount))
    except (InvalidOperation, ValueError):
        raise BankingError("Invalid amount")

    if amount <= 0:
        raise BankingError("Amount must be greater than zero")

    return amount


def _get_user_account_for_update(user, account_id):
    try:
        return Account.objects.select_for_update().get(id=account_id, owner=user)
    except Account.DoesNotExist:
        raise BankingError("Account not found or access denied")


@transaction.atomic
def deposit_to_account(user, account_id, amount):
    amount = _clean_amount(amount)
    account = _get_user_account_for_update(user, account_id)

    account.balance += amount
    account.save(update_fields=["balance"])

    new_transaction = Transaction.objects.create(
        account=account,
        transaction_type=Transaction.TYPE_DEPOSIT,
        amount=amount,
        destination_account=account,
        description="Simulated deposit",
    )

    ActivityLog.objects.create(
        user=user,
        action_type=ActivityLog.ACTION_DEPOSIT,
        details=f"Deposited ${amount} into account {account.account_number}",
    )

    return new_transaction


@transaction.atomic
def withdraw_from_account(user, account_id, amount):
    amount = _clean_amount(amount)
    account = _get_user_account_for_update(user, account_id)

    if account.balance < amount:
        raise BankingError("Insufficient funds")

    account.balance -= amount
    account.save(update_fields=["balance"])

    new_transaction = Transaction.objects.create(
        account=account,
        transaction_type=Transaction.TYPE_WITHDRAWAL,
        amount=amount,
        source_account=account,
        description="Simulated withdrawal",
    )

    ActivityLog.objects.create(
        user=user,
        action_type=ActivityLog.ACTION_WITHDRAWAL,
        details=f"Withdrew ${amount} from account {account.account_number}",
    )

    return new_transaction


@transaction.atomic
def transfer_between_accounts(user, source_account_id, destination_account_id, amount):
    amount = _clean_amount(amount)

    if source_account_id == destination_account_id:
        raise BankingError("Source and destination accounts must be different")

    source_account = _get_user_account_for_update(user, source_account_id)
    destination_account = _get_user_account_for_update(user, destination_account_id)

    if source_account.balance < amount:
        raise BankingError("Insufficient funds")

    source_account.balance -= amount
    destination_account.balance += amount

    source_account.save(update_fields=["balance"])
    destination_account.save(update_fields=["balance"])

    transfer_out = Transaction.objects.create(
        account=source_account,
        transaction_type=Transaction.TYPE_TRANSFER_OUT,
        amount=amount,
        source_account=source_account,
        destination_account=destination_account,
        description="Transfer out",
    )

    Transaction.objects.create(
        account=destination_account,
        transaction_type=Transaction.TYPE_TRANSFER_IN,
        amount=amount,
        source_account=source_account,
        destination_account=destination_account,
        description="Transfer in",
    )

    ActivityLog.objects.create(
        user=user,
        action_type=ActivityLog.ACTION_TRANSFER,
        details=(
            f"Transferred ${amount} from account {source_account.account_number} "
            f"to account {destination_account.account_number}"
        ),
    )

    return transfer_out