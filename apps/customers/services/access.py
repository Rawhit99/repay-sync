from django.db.models import QuerySet

from apps.accounts.models import Team, User
from apps.common.hierarchy import get_reporting_tree
from apps.common.request_context import get_request_access_service
from apps.customers.models import Customer, CustomerAssignment


class CustomerAccessService:
    """Resolves customer access for a user; reuses hierarchy tree within one instance."""

    __slots__ = ("_user", "_tree", "_officer_ids")

    def __init__(self, user: User):
        self._user = user
        self._tree = None
        self._officer_ids = None

    @property
    def has_unrestricted_access(self) -> bool:
        return self._user.is_superuser or self._user.team == Team.CALLING

    @property
    def officer_ids(self) -> frozenset:
        if self._officer_ids is None:
            if self.has_unrestricted_access or self._user.team != Team.FIELD:
                self._officer_ids = frozenset()
            else:
                self._tree = get_reporting_tree()
                self._officer_ids = self._tree.subordinate_officer_ids(self._user)
        return self._officer_ids

    def filter_customers(self, queryset: QuerySet[Customer]) -> QuerySet[Customer]:
        if self.has_unrestricted_access:
            return queryset
        if not self.officer_ids:
            return queryset.none()
        return queryset.filter(assignments__officer_id__in=self.officer_ids).distinct()

    def can_access(self, customer: Customer) -> bool:
        if self.has_unrestricted_access:
            return True
        if not self.officer_ids:
            return False
        return CustomerAssignment.objects.filter(
            customer_id=customer.pk,
            officer_id__in=self.officer_ids,
        ).exists()

    def can_modify_customer_records(self, customer: Customer) -> bool:
        """Field users may update records for customers they can access."""
        return self.can_access(customer)


def get_access_service(user: User) -> CustomerAccessService:
    return get_request_access_service(user)


def has_unrestricted_customer_access(user: User) -> bool:
    return get_access_service(user).has_unrestricted_access


def filter_customers_for_user(queryset: QuerySet[Customer], user: User) -> QuerySet[Customer]:
    return get_access_service(user).filter_customers(queryset)


def user_can_access_customer(user: User, customer: Customer) -> bool:
    return get_access_service(user).can_access(customer)
