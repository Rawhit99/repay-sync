from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import Role, Team, User
from apps.customers.models import Customer, CustomerAssignment
from apps.interactions.models import Disposition, Interaction

DEMO_PASSWORD = "demo123456"
DEMO_USERS = [
    ("senior@example.com", "Sam Senior", Team.FIELD, Role.SENIOR_MANAGER, None),
    ("manager1@example.com", "John Manager", Team.FIELD, Role.MANAGER, "senior@example.com"),
    ("officer1@example.com", "Jane Officer", Team.FIELD, Role.COLLECTION_OFFICER, "manager1@example.com"),
    ("officer2@example.com", "Bob Officer", Team.FIELD, Role.COLLECTION_OFFICER, "manager1@example.com"),
    ("agent1@example.com", "Alice Agent", Team.CALLING, Role.CALLING_AGENT, None),
]


class Command(BaseCommand):
    help = "Seed demo users, customers, assignments, and interactions."

    def handle(self, *args, **options):
        users_by_email: dict[str, User] = {}

        for email, full_name, team, role, manager_email in DEMO_USERS:
            manager = users_by_email.get(manager_email) if manager_email else None
            user, _ = User.objects.get_or_create(
                email=email,
                defaults={
                    "full_name": full_name,
                    "team": team,
                    "role": role,
                    "reports_to": manager,
                },
            )
            user.set_password(DEMO_PASSWORD)
            user.is_active = True
            user.save(update_fields=["password", "is_active"])
            users_by_email[email] = user

        officer1 = users_by_email["officer1@example.com"]
        officer2 = users_by_email["officer2@example.com"]
        agent = users_by_email["agent1@example.com"]

        customers_data = [
            ("CUST-001", "Acme Corp", "+1-555-0101", officer1),
            ("CUST-002", "Beta LLC", "+1-555-0102", officer1),
            ("CUST-003", "Gamma Inc", "+1-555-0103", officer2),
        ]

        for external_id, name, phone, officer in customers_data:
            customer, created = Customer.objects.get_or_create(
                external_id=external_id,
                defaults={"name": name, "phone": phone},
            )
            if created or not customer.assignments.exists():
                CustomerAssignment.objects.get_or_create(customer=customer, defaults={"officer": officer})

        c1 = Customer.objects.get(external_id="CUST-001")
        if not c1.interactions.exists():
            Interaction.objects.create(
                customer=c1,
                created_by=officer1,
                disposition=Disposition.PROMISE_TO_PAY,
                notes="Customer agreed to pay by Friday.",
                contacted_at=timezone.now(),
            )
            Interaction.objects.create(
                customer=c1,
                created_by=agent,
                disposition=Disposition.NO_ANSWER,
                notes="No answer on phone.",
                contacted_at=timezone.now() - timezone.timedelta(days=2),
            )

        self.stdout.write(self.style.SUCCESS("Demo data seeded successfully."))
        self.stdout.write(f"Password for all demo users: {DEMO_PASSWORD}")
        for email, *_ in DEMO_USERS:
            self.stdout.write(f"  - {email}")
