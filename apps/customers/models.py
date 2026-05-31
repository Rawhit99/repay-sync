import uuid

from django.db import models
from django.utils import timezone


class Customer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    external_id = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "customers"
        ordering = ["external_id"]

    def __str__(self):
        return self.external_id


class CustomerAssignment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    officer = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="customer_assignments",
    )
    assigned_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "customer_assignments"
        constraints = [
            models.UniqueConstraint(fields=["customer"], name="unique_active_customer_assignment"),
        ]

    def __str__(self):
        return f"{self.customer.external_id} -> {self.officer.email}"
