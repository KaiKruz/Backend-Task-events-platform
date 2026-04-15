from __future__ import annotations

from django.contrib import admin

from accounts.models import AccountProfile, EmailOTP


@admin.register(AccountProfile)
class AccountProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "email_verified")
    list_filter = ("role", "email_verified")
    search_fields = ("user__email", "user__username")


@admin.register(EmailOTP)
class EmailOTPAdmin(admin.ModelAdmin):
    list_display = ("user", "expires_at", "attempts_left", "is_used", "last_sent_at")
    list_filter = ("is_used",)
    readonly_fields = ("code_hash",)
