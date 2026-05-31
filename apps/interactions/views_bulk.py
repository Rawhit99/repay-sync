from rest_framework.permissions import IsAuthenticated

from apps.common.views import BaseBulkUploadView
from apps.interactions.services.bulk_interactions import bulk_create_interactions_from_csv


class InteractionBulkUploadView(BaseBulkUploadView):
    permission_classes = [IsAuthenticated]
    audit_resource_type = "interaction"

    def process_upload(self, content, user):
        return bulk_create_interactions_from_csv(content, user)
