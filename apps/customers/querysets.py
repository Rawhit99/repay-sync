from django.db.models import OuterRef, Subquery

from apps.customers.models import Customer
from apps.interactions.models import Interaction

_LATEST_INTERACTION = Interaction.objects.filter(customer=OuterRef("pk")).order_by(
    "-contacted_at", "-created_at"
)


def annotate_latest_disposition(queryset):
    return queryset.annotate(
        latest_disposition=Subquery(_LATEST_INTERACTION.values("disposition")[:1]),
        latest_contacted_at=Subquery(_LATEST_INTERACTION.values("contacted_at")[:1]),
    )


def get_customer_queryset():
    return annotate_latest_disposition(Customer.objects.all())
