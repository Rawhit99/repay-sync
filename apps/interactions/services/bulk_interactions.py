from functools import reduce
from operator import or_

from django.db.models import Q

from apps.accounts.models import User
from apps.common.csv_utils import BulkUploadResult, parse_contacted_at, parse_csv, strip_row, validate_columns
from apps.customers.models import Customer
from apps.customers.services.access import user_can_access_customer
from apps.interactions.models import Disposition, Interaction


REQUIRED_COLUMNS = frozenset({"customer_external_id", "user_email", "disposition", "notes", "contacted_at"})


def _lookup_customers(external_ids: set[str]) -> dict[str, Customer]:
    if not external_ids:
        return {}
    return {customer.external_id: customer for customer in Customer.objects.filter(external_id__in=external_ids)}


def _lookup_users(emails: set[str]) -> dict[str, User]:
    if not emails:
        return {}
    condition = reduce(or_, (Q(email__iexact=email) for email in emails), Q())
    return {user.email.lower(): user for user in User.objects.filter(condition)}


def bulk_create_interactions_from_csv(file_content: bytes, uploading_user: User) -> BulkUploadResult:
    result = BulkUploadResult()
    fieldnames, reader = parse_csv(file_content)

    column_error = validate_columns(fieldnames, REQUIRED_COLUMNS)
    if column_error:
        result.errors.append({"row": 0, "message": column_error})
        return result

    parsed_rows: list[tuple[int, dict]] = []
    external_ids: set[str] = set()
    user_emails: set[str] = set()

    for row_num, raw_row in enumerate(reader, start=2):
        row = strip_row(raw_row)
        row["disposition"] = row.get("disposition", "").upper()
        parsed_rows.append((row_num, row))
        if row["customer_external_id"]:
            external_ids.add(row["customer_external_id"])
        if row["user_email"]:
            user_emails.add(row["user_email"])

    customers = _lookup_customers(external_ids)
    users = _lookup_users(user_emails)
    pending: list[tuple[int, str, Interaction]] = []

    for row_num, row in parsed_rows:
        external_id = row["customer_external_id"]
        disposition = row["disposition"]

        if not external_id:
            result.errors.append({"row": row_num, "message": "customer_external_id is required"})
            continue
        if disposition not in Disposition.values:
            result.errors.append({"row": row_num, "message": f"invalid disposition: {disposition}"})
            continue

        contacted_at = parse_contacted_at(row["contacted_at"])
        if contacted_at is None:
            result.errors.append({"row": row_num, "message": "invalid or missing contacted_at"})
            continue

        customer = customers.get(external_id)
        if customer is None:
            result.errors.append({"row": row_num, "message": f"customer not found: {external_id}"})
            continue

        actor = users.get(row["user_email"].lower()) if row["user_email"] else uploading_user
        if actor is None:
            result.errors.append({"row": row_num, "message": f"user not found: {row['user_email']}"})
            continue

        if not user_can_access_customer(uploading_user, customer):
            result.errors.append({"row": row_num, "message": f"no access to customer: {external_id}"})
            continue

        pending.append(
            (
                row_num,
                external_id,
                Interaction(
                    customer=customer,
                    created_by=actor,
                    disposition=disposition,
                    notes=row["notes"],
                    contacted_at=contacted_at,
                ),
            )
        )

    if not pending:
        return result

    created = Interaction.objects.bulk_create([interaction for _, _, interaction in pending])
    for (row_num, external_id, _), interaction in zip(pending, created):
        result.created.append(
            {"row": row_num, "id": str(interaction.pk), "customer_external_id": external_id}
        )

    return result
