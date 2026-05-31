import secrets
from dataclasses import dataclass, field

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models.functions import Lower

from apps.accounts.models import Role, Team, User
from apps.common.csv_utils import BulkRowError, BulkUploadResult, parse_csv, strip_row, validate_columns
from apps.common.exceptions import InvalidCSVError
from apps.common.hierarchy import invalidate_reporting_tree_cache
from apps.common.lookups import lookup_users_by_email
from apps.common.validators import format_django_validation_error


REQUIRED_COLUMNS = frozenset({"email", "full_name", "team", "role", "manager_email"})
MANAGER_ROLES_IN_CSV = frozenset({Role.MANAGER, Role.SENIOR_MANAGER})


@dataclass(slots=True)
class _UserRowValidator:
    existing_emails: set[str]
    seen_emails: set[str] = field(default_factory=set)

    def validate(self, row: dict, row_num: int) -> BulkRowError | None:
        email = row.get("email", "").lower()

        if not row.get("email"):
            return BulkRowError(row_num, "email is required", field="email")
        if not row.get("full_name"):
            return BulkRowError(row_num, "full_name is required", field="full_name")
        if email in self.seen_emails:
            return BulkRowError(row_num, "duplicate email in CSV", field="email", value=row["email"])
        if email in self.existing_emails:
            return BulkRowError(row_num, "user already exists", field="email", value=row["email"])

        self.seen_emails.add(email)

        if row["team"] not in Team.values:
            return BulkRowError(row_num, f"invalid team '{row['team']}'", field="team", value=row["team"])
        if row["role"] not in Role.values:
            return BulkRowError(row_num, f"invalid role '{row['role']}'", field="role", value=row["role"])

        if row["team"] == Team.CALLING:
            if row["role"] != Role.CALLING_AGENT:
                return BulkRowError(row_num, "calling team users must have CALLING_AGENT role", field="role")
            if row.get("manager_email"):
                return BulkRowError(row_num, "calling team users must not have a manager", field="manager_email")
            return None

        if row["role"] == Role.CALLING_AGENT:
            return BulkRowError(row_num, "field team users cannot have CALLING_AGENT role", field="role")
        if row["role"] == Role.COLLECTION_OFFICER and not row.get("manager_email"):
            return BulkRowError(row_num, "collection officers must have manager_email", field="manager_email")
        if row["role"] in MANAGER_ROLES_IN_CSV and row.get("manager_email"):
            return BulkRowError(
                row_num,
                "top-level managers must not have manager_email in bulk upload",
                field="manager_email",
            )
        return None


def _topological_sort(rows: list[dict]) -> list[dict]:
    by_email = {row["email"].lower(): row for row in rows}
    cache: dict[str, int] = {}

    def depth(row: dict) -> int:
        email = row["email"].lower()
        if email in cache:
            return cache[email]
        manager_email = row.get("manager_email", "").lower()
        if not manager_email:
            cache[email] = 0
        else:
            manager_row = by_email.get(manager_email)
            cache[email] = depth(manager_row) + 1 if manager_row else 1
        return cache[email]

    return sorted(rows, key=depth)


def bulk_create_users_from_csv(file_content: bytes) -> BulkUploadResult:
    result = BulkUploadResult()

    try:
        fieldnames, reader = parse_csv(file_content)
        validate_columns(fieldnames, REQUIRED_COLUMNS)
    except InvalidCSVError as exc:
        result.errors.append({"row": 0, "message": str(exc.detail), "code": exc.error_code})
        return result

    validator = _UserRowValidator(
        existing_emails=set(User.objects.annotate(lower_email=Lower("email")).values_list("lower_email", flat=True))
    )
    pending: list[tuple[int, dict]] = []

    for row_num, raw_row in enumerate(reader, start=2):
        row = strip_row(raw_row)
        row["team"] = row.get("team", "").upper()
        row["role"] = row.get("role", "").upper()
        error = validator.validate(row, row_num)
        if error:
            result.errors.append(error.as_dict())
        else:
            pending.append((row_num, row))

    created_in_batch: dict[str, User] = {}
    row_num_map = {row["email"].lower(): row_num for row_num, row in pending}

    for row in _topological_sort([row for _, row in pending]):
        row_num = row_num_map[row["email"].lower()]
        email = row["email"]
        manager_email = row.get("manager_email", "")

        manager = None
        if manager_email:
            manager = created_in_batch.get(manager_email.lower())
            if manager is None:
                manager = lookup_users_by_email({manager_email}).get(manager_email.lower())
            if manager is None:
                result.errors.append(
                    BulkRowError(row_num, f"manager not found: {manager_email}", field="manager_email", value=manager_email).as_dict()
                )
                continue

        password = secrets.token_urlsafe(12)
        try:
            user = User(
                email=email,
                full_name=row["full_name"],
                team=row["team"],
                role=row["role"],
                reports_to=manager,
            )
            user.set_password(password)
            user.full_clean()
            user.save()
            created_in_batch[email.lower()] = user
            result.created.append({"row": row_num, "email": email, "password": password, "id": str(user.pk)})
        except DjangoValidationError as exc:
            result.errors.append(
                BulkRowError(row_num, format_django_validation_error(exc), field="email", value=email).as_dict()
            )
        except Exception as exc:
            result.errors.append(BulkRowError(row_num, str(exc), field="email", value=email).as_dict())

    if result.has_created:
        invalidate_reporting_tree_cache()

    return result
