from dataclasses import dataclass

from apps.accounts.models import User
from apps.common.csv_utils import BulkRowError, BulkUploadResult, parse_contacted_at, parse_csv, strip_row, validate_columns
from apps.common.exceptions import InvalidCSVError, InvalidDateTimeError
from apps.common.lookups import lookup_customers_by_external_id, lookup_users_by_email
from apps.customers.services.access import get_access_service
from apps.interactions.models import Disposition, Interaction


REQUIRED_COLUMNS = frozenset({"customer_external_id", "user_email", "disposition", "notes", "contacted_at"})


@dataclass(slots=True)
class _InteractionRowValidator:
    uploading_user: User
    customers: dict
    users: dict

    def validate(self, row: dict, row_num: int) -> tuple[BulkRowError | None, Interaction | None]:
        external_id = row.get("customer_external_id", "")
        disposition = row.get("disposition", "")

        if not external_id:
            return BulkRowError(row_num, "customer_external_id is required", field="customer_external_id"), None
        if disposition not in Disposition.values:
            return BulkRowError(
                row_num,
                f"invalid disposition '{disposition}'",
                field="disposition",
                value=disposition,
            ), None

        try:
            contacted_at = parse_contacted_at(row.get("contacted_at", ""), row=row_num)
        except InvalidDateTimeError as exc:
            return BulkRowError(row_num, str(exc.detail), field="contacted_at", value=row.get("contacted_at", "")), None

        customer = self.customers.get(external_id)
        if customer is None:
            return BulkRowError(
                row_num,
                f"customer not found: {external_id}",
                field="customer_external_id",
                value=external_id,
            ), None

        user_email = row.get("user_email", "")
        actor = self.users.get(user_email.lower()) if user_email else self.uploading_user
        if actor is None:
            return BulkRowError(
                row_num,
                f"user not found: {user_email}",
                field="user_email",
                value=user_email,
            ), None

        if not get_access_service(self.uploading_user).can_access(customer):
            return BulkRowError(
                row_num,
                f"no access to customer: {external_id}",
                field="customer_external_id",
                value=external_id,
            ), None

        interaction = Interaction(
            customer=customer,
            created_by=actor,
            disposition=disposition,
            notes=row.get("notes", ""),
            contacted_at=contacted_at,
        )
        return None, interaction


def bulk_create_interactions_from_csv(file_content: bytes, uploading_user: User) -> BulkUploadResult:
    result = BulkUploadResult()

    try:
        fieldnames, reader = parse_csv(file_content)
        validate_columns(fieldnames, REQUIRED_COLUMNS)
    except InvalidCSVError as exc:
        result.errors.append({"row": 0, "message": str(exc.detail), "code": exc.error_code})
        return result

    parsed_rows: list[tuple[int, dict]] = []
    external_ids: set[str] = set()
    user_emails: set[str] = set()

    for row_num, raw_row in enumerate(reader, start=2):
        row = strip_row(raw_row)
        row["disposition"] = row.get("disposition", "").upper()
        parsed_rows.append((row_num, row))
        if row.get("customer_external_id"):
            external_ids.add(row["customer_external_id"])
        if row.get("user_email"):
            user_emails.add(row["user_email"])

    validator = _InteractionRowValidator(
        uploading_user=uploading_user,
        customers=lookup_customers_by_external_id(external_ids),
        users=lookup_users_by_email(user_emails),
    )
    pending: list[tuple[int, str, Interaction]] = []

    for row_num, row in parsed_rows:
        error, interaction = validator.validate(row, row_num)
        if error:
            result.errors.append(error.as_dict())
        elif interaction is not None:
            pending.append((row_num, row["customer_external_id"], interaction))

    if not pending:
        return result

    created = Interaction.objects.bulk_create([interaction for _, _, interaction in pending])
    for (row_num, external_id, _), interaction in zip(pending, created):
        result.created.append({"row": row_num, "id": str(interaction.pk), "customer_external_id": external_id})

    return result
