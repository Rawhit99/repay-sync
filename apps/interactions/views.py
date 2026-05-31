from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated

from apps.accounts.permissions import CanModifyInteraction
from apps.audit.mixins import AuditLogMixin
from apps.audit.models import AuditAction
from apps.customers.models import Customer
from apps.customers.services.access import filter_customers_for_user
from apps.interactions.models import Interaction
from apps.interactions.serializers import (
    InteractionCreateSerializer,
    InteractionSerializer,
    InteractionUpdateSerializer,
)


class InteractionViewSet(
    AuditLogMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated, CanModifyInteraction]
    audit_resource_type = "interaction"

    def get_queryset(self):
        accessible_customers = filter_customers_for_user(
            Customer.objects.all(), self.request.user
        )
        return Interaction.objects.filter(customer__in=accessible_customers).select_related(
            "customer", "created_by"
        )

    def get_serializer_class(self):
        return {
            "create": InteractionCreateSerializer,
            "update": InteractionUpdateSerializer,
            "partial_update": InteractionUpdateSerializer,
        }.get(self.action, InteractionSerializer)

    def perform_create(self, serializer):
        interaction = serializer.save()
        self.set_audit(
            AuditAction.CREATE,
            resource_id=str(interaction.pk),
            customer_id=str(interaction.customer_id),
            disposition=interaction.disposition,
        )

    def retrieve(self, request, *args, **kwargs):
        self.set_audit(AuditAction.READ, resource_id=kwargs.get("pk", ""))
        return super().retrieve(request, *args, **kwargs)

    def perform_update(self, serializer):
        interaction = serializer.save()
        self.set_audit(AuditAction.UPDATE, resource_id=str(interaction.pk))
