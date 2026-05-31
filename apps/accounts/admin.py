from django.contrib import admin

from apps.accounts.models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("email", "full_name", "team", "role", "reports_to", "is_active")
    list_filter = ("team", "role", "is_active")
    search_fields = ("email", "full_name")
    raw_id_fields = ("reports_to",)
