import csv
import io
from dataclasses import dataclass, field
from datetime import datetime

from django.utils.dateparse import parse_datetime


@dataclass
class BulkUploadResult:
    created: list[dict] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)

    @property
    def has_created(self) -> bool:
        return bool(self.created)

    @property
    def has_errors(self) -> bool:
        return bool(self.errors)


def parse_csv(content: bytes) -> tuple[list[str] | None, csv.DictReader]:
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    return reader.fieldnames, reader


def validate_columns(fieldnames: list[str] | None, required: set[str]) -> str | None:
    if not fieldnames or not required.issubset(fieldnames):
        return f"CSV must include columns: {', '.join(sorted(required))}"
    return None


def parse_contacted_at(value: str) -> datetime | None:
    value = (value or "").strip()
    if not value:
        return None
    parsed = parse_datetime(value)
    if parsed:
        return parsed
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def strip_row(row: dict) -> dict:
    return {key: (value or "").strip() for key, value in row.items()}
