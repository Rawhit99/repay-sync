import secrets
from functools import reduce
from operator import or_

from django.db.models import Q
from django.db.models.functions import Lower

from apps.accounts.models import Role, Team, User
from apps.common.csv_utils import BulkUploadResult, parse_csv, strip_row, validate_columns


REQUIRED_COLUMNS = frozenset({"email", "full_name", "team", "role", "manager_email"})
MANAGER_ROLES_IN_CSV = frozenset({Role.MANAGER, Role.SENIOR_MANAGER})


def _validate_row(row: dict, existing_emails: set[str], seen_emails: set[str]) -> str | None:
    email = row["email"].lower()
    if email in seen_emails:
        return "duplicate email in CSV"
    if email in existing_emails:
        return f"user with email {row['email']} already exists"

    if not row["email"]:
        return "email is required"
    if not row["full_name"]:
        return "full_name is required"
    if row["team"] not in Team.values:
        return f"invalid team: {row['team']}"
    if row["role"] not in Role.values:
        return f"invalid role: {row['role']}"

    if row["team"] == Team.CALLING:
        if row["role"] != Role.CALLING_AGENT:
            return "calling team users must have CALLING_AGENT role"
        if row["manager_email"]:
            return "calling team users must not have a manager"
        return None

    if row["role"] == Role.CALLING_AGENT:
        return "field team users cannot have CALLING_AGENT role"
    if row["role"] == Role.COLLECTION_OFFICER and not row["manager_email"]:
        return "collection officers must have manager_email"
    if row["role"] in MANAGER_ROLES_IN_CSV and row["manager_email"]:
        return "managers should not have manager_email in bulk upload (top-level managers)"
    return None


def _topological_sort(rows: list[dict]) -> list[dict]:
    """Order rows so managers are created before their reports."""

    by_email = {row["email"].lower(): row for row in rows}

    def depth(row: dict, cache: dict[str, int]) -> int:
        email = row["email"].lower()
        if email in cache:
            return cache[email]
        manager_email = row["manager_email"].lower()
        if not manager_email:
            cache[email] = 0
        else:
            manager_row = by_email.get(manager_email)
            cache[email] = depth(manager_row, cache) + 1 if manager_row else 1
        return cache[email]

    cache: dict[str, int] = {}
    return sorted(rows, key=lambda row: depth(row, cache))


def _lookup_users_by_email(emails: set[str]) -> dict[str, User]:
    if not emails:
        return {}
    condition = reduce(or_, (Q(email__iexact=email) for email in emails), Q())
    return {user.email.lower(): user for user in User.objects.filter(condition)}


def bulk_create_users_from_csv(file_content: bytes) -> BulkUploadResult:
    result = BulkUploadResult()
    fieldnames, reader = parse_csv(file_content)

    column_error = validate_columns(fieldnames, REQUIRED_COLUMNS)
    if column_error:
        result.errors.append({"row": 0, "message": column_error})
        return result

    existing_emails = set(User.objects.annotate(lower_email=Lower("email")).values_list("lower_email", flat=True))
    pending: list[tuple[int, dict]] = []
    seen_emails: set[str] = set()

    for row_num, raw_row in enumerate(reader, start=2):
        row = strip_row(raw_row)
        row["team"] = row.get("team", "").upper()
        row["role"] = row.get("role", "").upper()
        error = _validate_row(row, existing_emails, seen_emails)
        seen_emails.add(row["email"].lower())

        if error:
            result.errors.append({"row": row_num, "email": row.get("email", ""), "message": error})
        else:
            pending.append((row_num, row))

    created_in_batch: dict[str, User] = {}
    row_num_map = {row["email"].lower(): row_num for row_num, row in pending}

    for row in _topological_sort([row for _, row in pending]):
        row_num = row_num_map[row["email"].lower()]
        email = row["email"]
        manager_email = row["manager_email"]

        manager = None
        if manager_email:
            manager = created_in_batch.get(manager_email.lower())
            if manager is None:
                manager = _lookup_users_by_email({manager_email}).get(manager_email.lower())
            if manager is None:
                result.errors.append(
                    {"row": row_num, "email": email, "message": f"manager not found: {manager_email}"}
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
        except Exception as exc:
            result.errors.append({"row": row_num, "email": email, "message": str(exc)})

    return result
