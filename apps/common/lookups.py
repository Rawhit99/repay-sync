from functools import reduce
from operator import or_

from django.db.models import Q

from apps.accounts.models import User
from apps.customers.models import Customer


def lookup_users_by_email(emails: set[str]) -> dict[str, User]:
    if not emails:
        return {}
    condition = reduce(or_, (Q(email__iexact=email) for email in emails), Q())
    return {user.email.lower(): user for user in User.objects.filter(condition)}


def lookup_customers_by_external_id(external_ids: set[str]) -> dict[str, Customer]:
    if not external_ids:
        return {}
    return {
        customer.external_id: customer
        for customer in Customer.objects.filter(external_id__in=external_ids)
    }
