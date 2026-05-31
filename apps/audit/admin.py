from django.contrib import admin

from apps.audit.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("action", "resource_type", "resource_id", "actor", "created_at")
    list_filter = ("action", "resource_type")
    search_fields = ("resource_id", "request_path", "actor__email")
    readonly_fields = (
        "id",
        "actor",
        "action",
        "resource_type",
        "resource_id",
        "ip_address",
        "request_method",
        "request_path",
        "metadata",
        "created_at",
    )
