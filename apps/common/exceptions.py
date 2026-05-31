from enum import StrEnum

from rest_framework import status
from rest_framework.exceptions import APIException


class ErrorCode(StrEnum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    CUSTOMER_ACCESS_DENIED = "CUSTOMER_ACCESS_DENIED"
    INVALID_CSV = "INVALID_CSV"
    INVALID_FILE = "INVALID_FILE"
    BULK_UPLOAD_FAILED = "BULK_UPLOAD_FAILED"
    DUPLICATE_RESOURCE = "DUPLICATE_RESOURCE"
    INVALID_DISPOSITION = "INVALID_DISPOSITION"
    INVALID_DATETIME = "INVALID_DATETIME"
    USER_NOT_FOUND = "USER_NOT_FOUND"
    CUSTOMER_NOT_FOUND = "CUSTOMER_NOT_FOUND"
    MANAGER_NOT_FOUND = "MANAGER_NOT_FOUND"


class RepaySyncAPIException(APIException):
    """Base API exception with stable error code and optional structured details."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_code = ErrorCode.VALIDATION_ERROR
    default_detail = "Request could not be processed."

    def __init__(self, detail=None, *, code=None, details=None):
        self.error_code = code or self.default_code
        self.details = details or {}
        super().__init__(detail=detail or self.default_detail)


class ValidationFailedError(RepaySyncAPIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = ErrorCode.VALIDATION_ERROR
    default_detail = "Validation failed."


class PermissionDeniedError(RepaySyncAPIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_code = ErrorCode.PERMISSION_DENIED
    default_detail = "You do not have permission to perform this action."


class CustomerAccessDeniedError(PermissionDeniedError):
    default_code = ErrorCode.CUSTOMER_ACCESS_DENIED
    default_detail = "You do not have access to this customer."


class NotFoundError(RepaySyncAPIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_code = ErrorCode.NOT_FOUND
    default_detail = "Resource not found."


class ConflictError(RepaySyncAPIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = ErrorCode.CONFLICT
    default_detail = "Resource conflict."


class DuplicateResourceError(ConflictError):
    default_code = ErrorCode.DUPLICATE_RESOURCE
    default_detail = "Resource already exists."


class InvalidCSVError(RepaySyncAPIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = ErrorCode.INVALID_CSV
    default_detail = "Invalid CSV file."


class InvalidFileError(RepaySyncAPIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = ErrorCode.INVALID_FILE
    default_detail = "Invalid upload file."


class InvalidDispositionError(ValidationFailedError):
    default_code = ErrorCode.INVALID_DISPOSITION
    default_detail = "Invalid disposition value."


class InvalidDateTimeError(ValidationFailedError):
    default_code = ErrorCode.INVALID_DATETIME
    default_detail = "Invalid datetime value."


class UserNotFoundError(NotFoundError):
    default_code = ErrorCode.USER_NOT_FOUND
    default_detail = "User not found."


class CustomerNotFoundError(NotFoundError):
    default_code = ErrorCode.CUSTOMER_NOT_FOUND
    default_detail = "Customer not found."


class ManagerNotFoundError(NotFoundError):
    default_code = ErrorCode.MANAGER_NOT_FOUND
    default_detail = "Manager not found."
