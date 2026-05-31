from django.core.exceptions import ValidationError as DjangoValidationError

from apps.common.exceptions import InvalidFileError

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB
ALLOWED_CSV_CONTENT_TYPES = {
    "text/csv",
    "application/csv",
    "text/plain",
    "application/vnd.ms-excel",
}


def validate_uploaded_csv(upload) -> bytes:
    if upload is None:
        raise InvalidFileError(
            "CSV file is required.",
            details={"field": "file", "hint": "Send the file as multipart form field 'file'."},
        )

    if upload.size == 0:
        raise InvalidFileError("Uploaded file is empty.", details={"field": "file"})

    if upload.size > MAX_UPLOAD_BYTES:
        raise InvalidFileError(
            f"File exceeds maximum size of {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.",
            details={"field": "file", "max_bytes": MAX_UPLOAD_BYTES},
        )

    content_type = getattr(upload, "content_type", "") or ""
    if content_type and content_type not in ALLOWED_CSV_CONTENT_TYPES:
        raise InvalidFileError(
            "Invalid file type. Upload a CSV file.",
            details={"field": "file", "content_type": content_type},
        )

    try:
        return upload.read()
    except OSError as exc:
        raise InvalidFileError("Unable to read uploaded file.", details={"reason": str(exc)}) from exc


def format_django_validation_error(exc: DjangoValidationError) -> str:
    if hasattr(exc, "message_dict"):
        return "; ".join(f"{field}: {', '.join(map(str, messages))}" for field, messages in exc.message_dict.items())
    if hasattr(exc, "messages"):
        return "; ".join(map(str, exc.messages))
    return str(exc)
