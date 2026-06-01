from django.db import transaction

from rest_framework import serializers

from apps.accounts.models import Role, Team, User
from apps.common.exceptions import (
    DuplicateResourceError,
    UserNotFoundError,
    ValidationFailedError,
)
from apps.customers.models import Customer, CustomerAssignment
from apps.customers.services.access import get_access_service


def _resolve_collection_officer(email: str) -> User:
    officer = User.objects.filter(email__iexact=email).only("role", "email", "pk").first()
    if officer is None:
        raise UserNotFoundError(
            "Assigned officer not found.",
            details={"field": "assigned_officer_email", "value": email},
        )
    if officer.role != Role.COLLECTION_OFFICER:
        raise ValidationFailedError(
            "Assigned user must be a collection officer.",
            details={"field": "assigned_officer_email", "role": officer.role},
        )
    return officer


def assign_customer_to_officer(customer: Customer, officer: User) -> CustomerAssignment:
    assignment = customer.assignments.first()
    if assignment:
        assignment.officer = officer
        assignment.save(update_fields=["officer"])
        return assignment
    return CustomerAssignment.objects.create(customer=customer, officer=officer)


class AssignedOfficerEmailMixin:
    def validate_assigned_officer_email(self, value):
        if not value:
            return value
        return _resolve_collection_officer(value).email


class CustomerListSerializer(serializers.ModelSerializer):
    latest_disposition = serializers.CharField(read_only=True, allow_null=True)
    latest_contacted_at = serializers.DateTimeField(read_only=True, allow_null=True)
    assigned_officer = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = (
            "id",
            "external_id",
            "name",
            "phone",
            "latest_disposition",
            "latest_contacted_at",
            "assigned_officer",
            "created_at",
        )

    def get_assigned_officer(self, obj):
        assignment = next(iter(obj.assignments.all()), None)
        if assignment is None:
            return None
        officer = assignment.officer
        return {"id": officer.pk, "email": officer.email, "full_name": officer.full_name}


class CustomerDetailSerializer(CustomerListSerializer):
    class Meta(CustomerListSerializer.Meta):
        fields = CustomerListSerializer.Meta.fields + ("updated_at",)


class CustomerCreateSerializer(AssignedOfficerEmailMixin, serializers.ModelSerializer):
    assigned_officer_email = serializers.EmailField(required=False, write_only=True, allow_blank=True)

    class Meta:
        model = Customer
        fields = ("external_id", "name", "phone", "assigned_officer_email")

    def validate_external_id(self, value):
        value = value.strip()
        if not value:
            raise ValidationFailedError("external_id cannot be blank.", details={"field": "external_id"})
        if Customer.objects.filter(external_id=value).exists():
            raise DuplicateResourceError(
                "Customer with this external_id already exists.",
                details={"field": "external_id", "value": value},
            )
        return value

    @transaction.atomic
    def create(self, validated_data):
        officer_email = validated_data.pop("assigned_officer_email", None)
        customer = Customer.objects.create(**validated_data)
        if officer_email:
            officer = User.objects.get(email__iexact=officer_email)
            assign_customer_to_officer(customer, officer)
        return customer


class CustomerAssignSerializer(AssignedOfficerEmailMixin, serializers.Serializer):
    assigned_officer_email = serializers.EmailField()

    def validate_assigned_officer_email(self, value):
        officer = _resolve_collection_officer(value)
        request_user = self.context["request"].user
        access = get_access_service(request_user)

        if not access.has_unrestricted_access and request_user.team == Team.FIELD:
            if officer.pk not in access.officer_ids:
                raise ValidationFailedError(
                    "Officer is not in your reporting subtree.",
                    details={"field": "assigned_officer_email", "value": value},
                )
        return officer.email

    @transaction.atomic
    def save(self, **kwargs):
        customer = self.instance
        officer = User.objects.get(email__iexact=self.validated_data["assigned_officer_email"])
        assign_customer_to_officer(customer, officer)
        return customer
