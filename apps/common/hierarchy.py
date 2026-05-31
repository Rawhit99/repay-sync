from collections import defaultdict, deque
from dataclasses import dataclass
from threading import Lock
from uuid import UUID

from apps.accounts.models import MANAGER_ROLES, Role, Team, User


@dataclass(frozen=True, slots=True)
class ReportingTree:
    """Immutable adjacency map for field-team hierarchy (single DB read, O(1) lookups)."""

    children: dict[UUID, tuple[UUID, ...]]
    roles: dict[UUID, str]

    @classmethod
    def build(cls) -> "ReportingTree":
        rows = User.objects.filter(team=Team.FIELD, is_active=True).values_list(
            "pk", "role", "reports_to_id"
        )
        children: dict[UUID, list[UUID]] = defaultdict(list)
        roles: dict[UUID, str] = {}
        for pk, role, manager_id in rows:
            roles[pk] = role
            if manager_id:
                children[manager_id].append(pk)
        frozen_children = {manager_id: tuple(reports) for manager_id, reports in children.items()}
        return cls(children=frozen_children, roles=roles)

    def subordinate_officer_ids(self, root_user: User) -> frozenset[UUID]:
        if root_user.team != Team.FIELD:
            return frozenset()

        if root_user.role == Role.COLLECTION_OFFICER:
            return frozenset({root_user.pk})

        officer_ids: set[UUID] = set()
        queue: deque[UUID] = deque(self.children.get(root_user.pk, ()))

        while queue:
            user_id = queue.popleft()
            role = self.roles.get(user_id)
            if role == Role.COLLECTION_OFFICER:
                officer_ids.add(user_id)
            elif role in MANAGER_ROLES:
                queue.extend(self.children.get(user_id, ()))

        return frozenset(officer_ids)


class ReportingTreeCache:
    """Process-level cache with explicit invalidation when hierarchy changes."""

    __slots__ = ("_lock", "_tree", "_version")

    def __init__(self):
        self._lock = Lock()
        self._tree: ReportingTree | None = None
        self._version = 0

    @property
    def version(self) -> int:
        return self._version

    def get(self) -> ReportingTree:
        with self._lock:
            if self._tree is None:
                self._tree = ReportingTree.build()
            return self._tree

    def invalidate(self) -> None:
        with self._lock:
            self._version += 1
            self._tree = None


_tree_cache = ReportingTreeCache()


def get_reporting_tree() -> ReportingTree:
    state = None
    try:
        from apps.common.request_context import get_request_state

        state = get_request_state()
    except ImportError:
        pass

    if state is not None:
        cached = state.get("reporting_tree")
        cached_version = state.get("reporting_tree_version")
        if cached is not None and cached_version == _tree_cache.version:
            return cached
        tree = _tree_cache.get()
        state["reporting_tree"] = tree
        state["reporting_tree_version"] = _tree_cache.version
        return tree

    return _tree_cache.get()


def invalidate_reporting_tree_cache() -> None:
    _tree_cache.invalidate()
    state = None
    try:
        from apps.common.request_context import get_request_state

        state = get_request_state()
    except ImportError:
        pass
    if state is not None:
        state["reporting_tree"] = None
        state["reporting_tree_version"] = None
