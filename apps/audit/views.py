import django_filters
from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated

from apps.accounts.permissions import IsManagerOrSuperuser
from apps.audit.models import AuditLog
from apps.audit.serializers import AuditLogSerializer


class AuditLogFilter(django_filters.FilterSet):
    action = django_filters.CharFilter()
    resource_type = django_filters.CharFilter()
    actor = django_filters.UUIDFilter(field_name="actor_id")

    class Meta:
        model = AuditLog
        fields = ["action", "resource_type", "actor"]


class AuditLogViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = AuditLog.objects.select_related("actor").all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated, IsManagerOrSuperuser]
    filterset_class = AuditLogFilter
    ordering = ["-created_at"]
