import uuid

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone

from apps.accounts.managers import UserManager


class Team(models.TextChoices):
    FIELD = "FIELD", "Field"
    CALLING = "CALLING", "Calling"


class Role(models.TextChoices):
    COLLECTION_OFFICER = "COLLECTION_OFFICER", "Collection Officer"
    MANAGER = "MANAGER", "Manager"
    SENIOR_MANAGER = "SENIOR_MANAGER", "Senior Manager"
    CALLING_AGENT = "CALLING_AGENT", "Calling Agent"


FIELD_ROLES = {Role.COLLECTION_OFFICER, Role.MANAGER, Role.SENIOR_MANAGER}
MANAGER_ROLES = {Role.MANAGER, Role.SENIOR_MANAGER}


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255)
    team = models.CharField(max_length=20, choices=Team.choices)
    role = models.CharField(max_length=30, choices=Role.choices)
    reports_to = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="direct_reports",
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        db_table = "users"
        ordering = ["email"]

    def __str__(self):
        return self.email

    @property
    def is_calling_team(self):
        return self.team == Team.CALLING

    @property
    def is_field_team(self):
        return self.team == Team.FIELD

    @property
    def is_manager(self):
        return self.role in MANAGER_ROLES

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.team == Team.CALLING and self.role != Role.CALLING_AGENT:
            raise ValidationError({"role": "Calling team users must have CALLING_AGENT role."})
        if self.team == Team.FIELD and self.role == Role.CALLING_AGENT:
            raise ValidationError({"role": "Field team users cannot have CALLING_AGENT role."})
        if self.team == Team.CALLING and self.reports_to_id:
            raise ValidationError({"reports_to": "Calling team users cannot have a manager."})
        if self.team == Team.FIELD and self.role == Role.COLLECTION_OFFICER and not self.reports_to_id:
            raise ValidationError({"reports_to": "Collection officers must report to a manager."})
