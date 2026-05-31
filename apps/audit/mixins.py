from apps.audit.models import AuditAction
from apps.audit.services import log_audit_event


class AuditLogMixin:
    """Attach audit metadata on views; logs once per successful response."""

    audit_action = AuditAction.READ
    audit_resource_type = ""

    def initial(self, request, *args, **kwargs):
        self._audit_resource_id = ""
        self._audit_metadata = {}
        super().initial(request, *args, **kwargs)

    def set_audit(self, action: str | None = None, resource_id: str = "", **metadata):
        if action:
            self.audit_action = action
        if resource_id:
            self._audit_resource_id = resource_id
        if metadata:
            self._audit_metadata.update(metadata)

    def set_audit_metadata(self, **metadata):
        self._audit_metadata.update(metadata)

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)

        should_log = (
            request.user.is_authenticated
            and (response.status_code < 400 or self.audit_action == AuditAction.BULK_UPLOAD)
        )
        if not should_log:
            return response

        resource_id = self._audit_resource_id
        if not resource_id and isinstance(getattr(response, "data", None), dict):
            resource_id = str(response.data.get("id", ""))

        log_audit_event(
            actor=request.user,
            action=self.audit_action,
            resource_type=self.audit_resource_type,
            resource_id=resource_id,
            request=request,
            metadata=self._audit_metadata,
        )
        return response
