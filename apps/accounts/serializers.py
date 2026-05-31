from rest_framework import serializers

from apps.accounts.models import User


class UserSerializer(serializers.ModelSerializer):
    manager_email = serializers.EmailField(source="reports_to.email", read_only=True, default=None)

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "full_name",
            "team",
            "role",
            "manager_email",
            "is_active",
            "date_joined",
        )
        read_only_fields = fields
