from rest_framework.permissions import BasePermission, SAFE_METHODS

from apps.accounts.models import MANAGER_ROLES, Team
from apps.customers.services.access import get_access_service


class CanAccessCustomer(BasePermission):
    message = "You do not have access to this customer."

    def has_object_permission(self, request, view, obj):
        return get_access_service(request.user).can_access(obj)


class CanCreateCustomer(BasePermission):
    message = "Only managers or calling team members may create customers."

    def has_permission(self, request, view):
        if request.method != "POST":
            return True
        user = request.user
        return get_access_service(user).has_unrestricted_access or user.role in MANAGER_ROLES


class CanModifyInteraction(BasePermission):
    message = "You do not have permission to modify this interaction."

    def has_object_permission(self, request, view, obj):
        user = request.user
        access = get_access_service(user)

        if request.method in SAFE_METHODS:
            return access.can_access(obj.customer)

        if obj.created_by_id == user.pk or access.has_unrestricted_access:
            return True
        return user.team == Team.FIELD and user.role in MANAGER_ROLES and access.can_access(obj.customer)


class IsManagerOrSuperuser(BasePermission):
    message = "Manager or superuser access required."

    def has_permission(self, request, view):
        user = request.user
        return user.is_superuser or (user.team == Team.FIELD and user.role in MANAGER_ROLES)
