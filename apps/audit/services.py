SENSITIVE_KEYS = {"password", "token", "refresh", "access", "authorization", "secret"}


def sanitize_metadata(data: dict | None) -> dict:
    if not data:
        return {}
    sanitized = {}
    for key, value in data.items():
        if key.lower() in SENSITIVE_KEYS:
            sanitized[key] = "[REDACTED]"
        elif isinstance(value, dict):
            sanitized[key] = sanitize_metadata(value)
        else:
            sanitized[key] = value
    return sanitized


def get_client_ip(request) -> str | None:
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def log_audit_event(
    *,
    actor,
    action: str,
    resource_type: str = "",
    resource_id: str = "",
    request=None,
    metadata: dict | None = None,
):
    from apps.audit.models import AuditLog

    AuditLog.objects.create(
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=get_client_ip(request) if request else None,
        request_method=request.method if request else "",
        request_path=request.path if request else "",
        metadata=sanitize_metadata(metadata),
    )
