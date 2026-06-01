from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import CanAccessCustomer, CanAssignCustomer, CanCreateCustomer
from apps.audit.mixins import AuditLogMixin
from apps.audit.models import AuditAction
from apps.customers.querysets import get_customer_queryset
from apps.customers.serializers import (
    CustomerAssignSerializer,
    CustomerCreateSerializer,
    CustomerDetailSerializer,
    CustomerListSerializer,
)
from apps.customers.services.access import filter_customers_for_user, get_access_service
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
        if self.action == "assign":
            return CustomerAssignSerializer
        return {
            "create": CustomerCreateSerializer,
            "retrieve": CustomerDetailSerializer,
        }.get(self.action, CustomerListSerializer)

    def get_permissions(self):
        if self.action == "assign":
            return [IsAuthenticated(), CanAssignCustomer()]
        if self.action in ("retrieve", "interactions"):
            return [IsAuthenticated(), CanAccessCustomer()]
        return super().get_permissions()

    def get_object(self):
        if self.action != "assign":
            return super().get_object()

        queryset = get_customer_queryset().prefetch_related("assignments__officer")
        access = get_access_service(self.request.user)
        if not access.has_unrestricted_access:
            if not access.officer_ids:
                queryset = queryset.none()
            else:
                queryset = queryset.filter(
                    Q(assignments__officer_id__in=access.officer_ids) | Q(assignments__isnull=True)
                ).distinct()
        return get_object_or_404(queryset, pk=self.kwargs["pk"])

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

    @action(detail=True, methods=["patch"], url_path="assign")
    def assign(self, request, pk=None):
        customer = self.get_object()
        serializer = self.get_serializer(customer, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        self.set_audit(
            AuditAction.UPDATE,
            resource_id=str(customer.pk),
            external_id=customer.external_id,
            assigned_officer_email=serializer.validated_data["assigned_officer_email"],
        )
        customer = self.get_queryset().get(pk=customer.pk)
        return Response(CustomerDetailSerializer(customer).data)

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
