from rest_framework import status
from rest_framework.response import Response

from apps.audit.mixins import AuditLogMixin
from apps.audit.models import AuditAction
from apps.common.base_views import BaseAPIView
from apps.common.csv_utils import BulkUploadResult
from apps.common.validators import validate_uploaded_csv


class BaseBulkUploadView(AuditLogMixin, BaseAPIView):
    audit_action = AuditAction.BULK_UPLOAD

    def process_upload(self, content: bytes, user) -> BulkUploadResult:
        raise NotImplementedError

    @staticmethod
    def _response_status(result: BulkUploadResult) -> int:
        if result.has_created and result.has_errors:
            return status.HTTP_207_MULTI_STATUS
        if result.has_created:
            return status.HTTP_201_CREATED
        return status.HTTP_400_BAD_REQUEST

    def post(self, request):
        content = validate_uploaded_csv(request.FILES.get("file"))
        result = self.process_upload(content, request.user)
        self.set_audit_metadata(
            created_count=len(result.created),
            error_count=len(result.errors),
        )
        return Response(
            {
                "created": result.created,
                "errors": result.errors,
                "summary": {
                    "created_count": len(result.created),
                    "error_count": len(result.errors),
                },
            },
            status=self._response_status(result),
        )
