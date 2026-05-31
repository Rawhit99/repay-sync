import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class AuditAction(models.TextChoices):
    CREATE = "CREATE", "Create"
    READ = "READ", "Read"
    UPDATE = "UPDATE", "Update"
    DELETE = "DELETE", "Delete"
    BULK_UPLOAD = "BULK_UPLOAD", "Bulk Upload"
    LOGIN = "LOGIN", "Login"


class AuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=20, choices=AuditAction.choices)
    resource_type = models.CharField(max_length=100, blank=True)
    resource_id = models.CharField(max_length=100, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    request_method = models.CharField(max_length=10, blank=True)
    request_path = models.CharField(max_length=500, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "audit_logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["actor", "-created_at"]),
            models.Index(fields=["resource_type", "resource_id"]),
        ]

    def __str__(self):
        return f"{self.action} {self.resource_type} by {self.actor_id}"
