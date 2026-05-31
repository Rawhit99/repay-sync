from collections import defaultdict, deque

from django.db.models import QuerySet

from apps.accounts.models import MANAGER_ROLES, Role, Team, User
from apps.customers.models import Customer, CustomerAssignment


def _build_reporting_tree() -> tuple[dict, dict]:
    """Load field hierarchy into adjacency and role maps in a single query."""
    rows = User.objects.filter(team=Team.FIELD, is_active=True).values_list(
        "pk", "role", "reports_to_id"
    )
    children: dict = defaultdict(list)
    roles: dict = {}
    for pk, role, manager_id in rows:
        roles[pk] = role
        if manager_id:
            children[manager_id].append(pk)
    return children, roles


def get_subordinate_officer_ids(user: User) -> frozenset:
    """Return IDs of collection officers in the user's reporting subtree."""
    if user.team != Team.FIELD:
        return frozenset()

    if user.role == Role.COLLECTION_OFFICER:
        return frozenset({user.pk})

    children, roles = _build_reporting_tree()
    officer_ids: set = set()
    queue = deque(children.get(user.pk, []))

    while queue:
        uid = queue.popleft()
        role = roles.get(uid)
        if role == Role.COLLECTION_OFFICER:
            officer_ids.add(uid)
        elif role in MANAGER_ROLES:
            queue.extend(children.get(uid, []))

    return frozenset(officer_ids)


def has_unrestricted_customer_access(user: User) -> bool:
    return user.is_superuser or user.team == Team.CALLING


def filter_customers_for_user(queryset: QuerySet[Customer], user: User) -> QuerySet[Customer]:
    if has_unrestricted_customer_access(user):
        return queryset

    officer_ids = get_subordinate_officer_ids(user)
    if not officer_ids:
        return queryset.none()

    return queryset.filter(assignments__officer_id__in=officer_ids).distinct()


def user_can_access_customer(user: User, customer: Customer) -> bool:
    if has_unrestricted_customer_access(user):
        return True

    officer_ids = get_subordinate_officer_ids(user)
    return CustomerAssignment.objects.filter(
        customer_id=customer.pk,
        officer_id__in=officer_ids,
    ).exists()
