import uuid

from django.db import models
from django.utils import timezone


class Disposition(models.TextChoices):
    CONTACTED = "CONTACTED", "Contacted"
    NO_ANSWER = "NO_ANSWER", "No Answer"
    PROMISE_TO_PAY = "PROMISE_TO_PAY", "Promise to Pay"
    REFUSED = "REFUSED", "Refused"
    WRONG_NUMBER = "WRONG_NUMBER", "Wrong Number"
    CALLBACK_REQUESTED = "CALLBACK_REQUESTED", "Callback Requested"


class Interaction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.CASCADE,
        related_name="interactions",
    )
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="interactions",
    )
    disposition = models.CharField(max_length=30, choices=Disposition.choices)
    notes = models.TextField(blank=True)
    contacted_at = models.DateTimeField()
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "interactions"
        ordering = ["-contacted_at"]
        indexes = [
            models.Index(fields=["customer", "-contacted_at"]),
        ]

    def __str__(self):
        return f"{self.customer.external_id} - {self.disposition}"
