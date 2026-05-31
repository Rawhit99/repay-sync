from rest_framework import serializers

from apps.audit.models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.EmailField(source="actor.email", read_only=True, default=None)

    class Meta:
        model = AuditLog
        fields = (
            "id",
            "actor",
            "actor_email",
            "action",
            "resource_type",
            "resource_id",
            "ip_address",
            "request_method",
            "request_path",
            "metadata",
            "created_at",
        )
        read_only_fields = fields
