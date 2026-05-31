from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import CanAccessCustomer, CanCreateCustomer
from apps.audit.mixins import AuditLogMixin
from apps.audit.models import AuditAction
from apps.customers.querysets import get_customer_queryset
from apps.customers.serializers import (
    CustomerCreateSerializer,
    CustomerDetailSerializer,
    CustomerListSerializer,
)
from apps.customers.services.access import filter_customers_for_user
from apps.interactions.serializers import InteractionSerializer


class CustomerViewSet(
    AuditLogMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated, CanCreateCustomer]
    audit_resource_type = "customer"

    def get_queryset(self):
        queryset = get_customer_queryset().prefetch_related("assignments__officer")
        return filter_customers_for_user(queryset, self.request.user)

    def get_serializer_class(self):
        return {
            "create": CustomerCreateSerializer,
            "retrieve": CustomerDetailSerializer,
        }.get(self.action, CustomerListSerializer)

    def get_permissions(self):
        if self.action in ("retrieve", "interactions"):
            return [IsAuthenticated(), CanAccessCustomer()]
        return super().get_permissions()

    def perform_create(self, serializer):
        customer = serializer.save()
        self.set_audit(
            AuditAction.CREATE,
            resource_id=str(customer.pk),
            external_id=customer.external_id,
        )

    def retrieve(self, request, *args, **kwargs):
        self.set_audit(AuditAction.READ, resource_id=kwargs.get("pk", ""))
        return super().retrieve(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        self.set_audit(AuditAction.READ, list=True)
        return super().list(request, *args, **kwargs)

    @action(detail=True, methods=["get"], url_path="interactions")
    def interactions(self, request, pk=None):
        customer = self.get_object()
        queryset = customer.interactions.select_related("created_by").order_by(
            "-contacted_at", "-created_at"
        )
        page = self.paginate_queryset(queryset)
        serializer = InteractionSerializer(page if page is not None else queryset, many=True)
        self.set_audit(AuditAction.READ, resource_id=str(customer.pk), interaction_history=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)
