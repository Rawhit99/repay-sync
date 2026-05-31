from rest_framework import serializers

from apps.common.exceptions import CustomerAccessDeniedError, InvalidDispositionError
from apps.customers.services.access import get_access_service
from apps.interactions.models import Disposition, Interaction


class DispositionValidatorMixin:
    def validate_disposition(self, value):
        if value not in Disposition.values:
            raise InvalidDispositionError(
                details={
                    "field": "disposition",
                    "value": value,
                    "allowed": list(Disposition.values),
                }
            )
        return value


class InteractionSerializer(serializers.ModelSerializer):
    created_by_email = serializers.EmailField(source="created_by.email", read_only=True)
    created_by_name = serializers.CharField(source="created_by.full_name", read_only=True)
    customer_external_id = serializers.CharField(source="customer.external_id", read_only=True)

    class Meta:
        model = Interaction
        fields = (
            "id",
            "customer",
            "customer_external_id",
            "created_by",
            "created_by_email",
            "created_by_name",
            "disposition",
            "notes",
            "contacted_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_by", "created_at", "updated_at")


class InteractionCreateSerializer(DispositionValidatorMixin, serializers.ModelSerializer):
    disposition = serializers.ChoiceField(choices=Disposition.choices)

    class Meta:
        model = Interaction
        fields = ("customer", "disposition", "notes", "contacted_at")

    def validate(self, attrs):
        user = self.context["request"].user
        customer = attrs["customer"]
        if not get_access_service(user).can_access(customer):
            raise CustomerAccessDeniedError(
                details={"customer_id": str(customer.pk), "external_id": customer.external_id}
            )
        return attrs

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)


class InteractionUpdateSerializer(DispositionValidatorMixin, serializers.ModelSerializer):
    disposition = serializers.ChoiceField(choices=Disposition.choices)

    class Meta:
        model = Interaction
        fields = ("disposition", "notes", "contacted_at")
