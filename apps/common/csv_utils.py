import csv
import io
from dataclasses import dataclass, field
from datetime import datetime

from django.utils.dateparse import parse_datetime

from apps.common.exceptions import InvalidCSVError, InvalidDateTimeError


@dataclass(slots=True)
class BulkUploadResult:
    created: list[dict] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)

    @property
    def has_created(self) -> bool:
        return bool(self.created)

    @property
    def has_errors(self) -> bool:
        return bool(self.errors)


@dataclass(frozen=True, slots=True)
class BulkRowError:
    row: int
    message: str
    field: str = ""
    value: str = ""

    def as_dict(self) -> dict:
        payload = {"row": self.row, "message": self.message}
        if self.field:
            payload["field"] = self.field
        if self.value:
            payload["value"] = self.value
        return payload


def parse_csv(content: bytes) -> tuple[list[str] | None, csv.DictReader]:
    if not content.strip():
        raise InvalidCSVError("CSV file is empty.", details={"field": "file"})

    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise InvalidCSVError(
            "CSV must be UTF-8 encoded.",
            details={"field": "file", "reason": str(exc)},
        ) from exc

    reader = csv.DictReader(io.StringIO(text))
    return reader.fieldnames, reader


def validate_columns(fieldnames: list[str] | None, required: set[str]) -> None:
    if not fieldnames:
        raise InvalidCSVError(
            "CSV header row is missing.",
            details={"required_columns": sorted(required)},
        )
    missing = required - set(fieldnames)
    if missing:
        raise InvalidCSVError(
            "CSV is missing required columns.",
            details={"missing_columns": sorted(missing), "required_columns": sorted(required)},
        )


def parse_contacted_at(value: str, *, row: int = 0) -> datetime:
    value = (value or "").strip()
    if not value:
        raise InvalidDateTimeError(
            "contacted_at is required.",
            details={"row": row, "field": "contacted_at"},
        )

    parsed = parse_datetime(value)
    if parsed is None:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise InvalidDateTimeError(
                "contacted_at must be ISO-8601 (e.g. 2026-05-28T10:30:00Z).",
                details={"row": row, "field": "contacted_at", "value": value},
            ) from exc

    return parsed


def strip_row(row: dict) -> dict:
    return {key: (value or "").strip() for key, value in row.items()}
