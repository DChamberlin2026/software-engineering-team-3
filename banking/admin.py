from django.contrib import admin

from .models import Account, ActivityLog, Transaction, UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role")
    search_fields = ("user__username", "user__email")
    list_filter = ("role",)


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("account_number", "account_name", "account_type", "owner", "balance")
    search_fields = ("account_number", "account_name", "owner__username")
    list_filter = ("account_type",)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("account", "transaction_type", "amount", "transaction_date")
    search_fields = ("account__account_number", "account__owner__username")
    list_filter = ("transaction_type", "transaction_date")


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ("user", "action_type", "action_datetime")
    search_fields = ("user__username", "details")
    list_filter = ("action_type", "action_datetime")