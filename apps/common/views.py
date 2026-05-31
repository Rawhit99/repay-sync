from rest_framework import status
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.mixins import AuditLogMixin
from apps.audit.models import AuditAction
from apps.common.csv_utils import BulkUploadResult


class BaseBulkUploadView(AuditLogMixin, APIView):
    parser_classes = [MultiPartParser]
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
        upload = request.FILES.get("file")
        if not upload:
            return Response(
                {"detail": "CSV file is required (field name: file)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = self.process_upload(upload.read(), request.user)
        self.set_audit_metadata(
            created_count=len(result.created),
            error_count=len(result.errors),
        )
        return Response(
            {"created": result.created, "errors": result.errors},
            status=self._response_status(result),
        )
