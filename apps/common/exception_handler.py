from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler

from apps.common.exceptions import ErrorCode, RepaySyncAPIException


def _normalize_field_errors(data: dict) -> dict:
    normalized = {}
    for field, messages in data.items():
        if isinstance(messages, dict):
            normalized[field] = _normalize_field_errors(messages)
        elif isinstance(messages, list):
            normalized[field] = [str(message) for message in messages]
        else:
            normalized[field] = str(messages)
    return normalized


def repay_sync_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if isinstance(exc, RepaySyncAPIException):
        return Response(
            {
                "error": {
                    "code": exc.error_code,
                    "message": str(exc.detail),
                    "details": exc.details,
                }
            },
            status=exc.status_code,
        )

    if isinstance(exc, ValidationError):
        details = _normalize_field_errors(exc.detail) if isinstance(exc.detail, dict) else {"non_field_errors": exc.detail}
        return Response(
            {
                "error": {
                    "code": ErrorCode.VALIDATION_ERROR,
                    "message": "Validation failed.",
                    "details": details,
                }
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if isinstance(exc, PermissionDenied):
        return Response(
            {
                "error": {
                    "code": ErrorCode.PERMISSION_DENIED,
                    "message": str(exc.detail),
                    "details": {},
                }
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    if response is not None:
        message = response.data.get("detail", response.data) if isinstance(response.data, dict) else response.data
        return Response(
            {
                "error": {
                    "code": _status_to_code(response.status_code),
                    "message": str(message),
                    "details": {},
                }
            },
            status=response.status_code,
        )

    return response


def _status_to_code(status_code: int) -> str:
    mapping = {
        401: ErrorCode.AUTHENTICATION_FAILED,
        403: ErrorCode.PERMISSION_DENIED,
        404: ErrorCode.NOT_FOUND,
        409: ErrorCode.CONFLICT,
    }
    return mapping.get(status_code, ErrorCode.VALIDATION_ERROR)
