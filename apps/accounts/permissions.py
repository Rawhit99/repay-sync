from rest_framework.permissions import BasePermission, SAFE_METHODS

from apps.accounts.models import MANAGER_ROLES, Team
from apps.customers.services.access import has_unrestricted_customer_access, user_can_access_customer


class CanAccessCustomer(BasePermission):
    message = "You do not have access to this customer."

    def has_object_permission(self, request, view, obj):
        return user_can_access_customer(request.user, obj)


class CanCreateCustomer(BasePermission):
    message = "You do not have permission to create customers."

    def has_permission(self, request, view):
        if request.method != "POST":
            return True
        user = request.user
        return has_unrestricted_customer_access(user) or user.role in MANAGER_ROLES


class CanModifyInteraction(BasePermission):
    message = "You do not have permission to modify this interaction."

    def has_object_permission(self, request, view, obj):
        user = request.user
        if request.method in SAFE_METHODS:
            return user_can_access_customer(user, obj.customer)

        if obj.created_by_id == user.pk or has_unrestricted_customer_access(user):
            return True
        return user.team == Team.FIELD and user.role in MANAGER_ROLES and user_can_access_customer(
            user, obj.customer
        )


class IsManagerOrSuperuser(BasePermission):
    message = "Manager access required."

    def has_permission(self, request, view):
        user = request.user
        return user.is_superuser or (user.team == Team.FIELD and user.role in MANAGER_ROLES)
