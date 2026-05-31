from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Role, Team, User
from apps.customers.models import Customer, CustomerAssignment
from apps.interactions.models import Disposition, Interaction


def csv_upload(name: str, content: str) -> SimpleUploadedFile:
    return SimpleUploadedFile(name, content.encode("utf-8"), content_type="text/csv")


class RepaySyncTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.senior = User.objects.create_user(
            email="senior@example.com",
            password="pass123456",
            full_name="Senior Manager",
            team=Team.FIELD,
            role=Role.SENIOR_MANAGER,
        )
        self.manager = User.objects.create_user(
            email="manager@example.com",
            password="pass123456",
            full_name="Manager",
            team=Team.FIELD,
            role=Role.MANAGER,
            reports_to=self.senior,
        )
        self.officer = User.objects.create_user(
            email="officer@example.com",
            password="pass123456",
            full_name="Officer",
            team=Team.FIELD,
            role=Role.COLLECTION_OFFICER,
            reports_to=self.manager,
        )
        self.other_officer = User.objects.create_user(
            email="other@example.com",
            password="pass123456",
            full_name="Other Officer",
            team=Team.FIELD,
            role=Role.COLLECTION_OFFICER,
            reports_to=self.manager,
        )
        self.agent = User.objects.create_user(
            email="agent@example.com",
            password="pass123456",
            full_name="Agent",
            team=Team.CALLING,
            role=Role.CALLING_AGENT,
        )
        self.customer_assigned = Customer.objects.create(external_id="CUST-A", name="Assigned")
        self.customer_other = Customer.objects.create(external_id="CUST-B", name="Other")
        CustomerAssignment.objects.create(customer=self.customer_assigned, officer=self.officer)
        CustomerAssignment.objects.create(customer=self.customer_other, officer=self.other_officer)

    def authenticate(self, user):
        self.client.force_authenticate(user=user)


class AuthTests(RepaySyncTestCase):
    def test_jwt_login_with_email(self):
        response = self.client.post(
            "/api/v1/auth/token/",
            {"email": "agent@example.com", "password": "pass123456"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)


class PermissionTests(RepaySyncTestCase):
    def test_officer_cannot_access_unassigned_customer(self):
        self.authenticate(self.officer)
        response = self.client.get(f"/api/v1/customers/{self.customer_other.pk}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_manager_sees_subtree_customers(self):
        self.authenticate(self.manager)
        response = self.client.get("/api/v1/customers/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        external_ids = {item["external_id"] for item in response.data["results"]}
        self.assertEqual(external_ids, {"CUST-A", "CUST-B"})

    def test_calling_agent_sees_all_customers(self):
        self.authenticate(self.agent)
        response = self.client.get("/api/v1/customers/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)


class LatestDispositionTests(RepaySyncTestCase):
    def test_customer_list_shows_latest_disposition(self):
        Interaction.objects.create(
            customer=self.customer_assigned,
            created_by=self.officer,
            disposition=Disposition.NO_ANSWER,
            notes="Old",
            contacted_at=timezone.now() - timezone.timedelta(days=1),
        )
        Interaction.objects.create(
            customer=self.customer_assigned,
            created_by=self.officer,
            disposition=Disposition.PROMISE_TO_PAY,
            notes="Latest",
            contacted_at=timezone.now(),
        )
        self.authenticate(self.officer)
        response = self.client.get("/api/v1/customers/")
        item = next(r for r in response.data["results"] if r["external_id"] == "CUST-A")
        self.assertEqual(item["latest_disposition"], Disposition.PROMISE_TO_PAY)


class BulkUploadTests(RepaySyncTestCase):
    def test_bulk_user_upload_returns_credentials(self):
        self.authenticate(self.senior)
        csv_content = (
            "email,full_name,team,role,manager_email\n"
            "newofficer@example.com,New Officer,FIELD,COLLECTION_OFFICER,manager@example.com\n"
        )
        response = self.client.post(
            "/api/v1/users/bulk-upload/",
            {"file": csv_upload("users.csv", csv_content)},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data["created"]), 1)
        self.assertIn("password", response.data["created"][0])
        self.assertTrue(User.objects.filter(email="newofficer@example.com").exists())

    def test_bulk_interaction_upload_respects_access(self):
        self.authenticate(self.officer)
        csv_content = (
            "customer_external_id,user_email,disposition,notes,contacted_at\n"
            "CUST-B,officer@example.com,CONTACTED,Should fail,2026-05-28T10:30:00Z\n"
            "CUST-A,officer@example.com,CONTACTED,Should succeed,2026-05-28T10:30:00Z\n"
        )
        response = self.client.post(
            "/api/v1/interactions/bulk-upload/",
            {"file": csv_upload("interactions.csv", csv_content)},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_207_MULTI_STATUS)
        self.assertEqual(len(response.data["created"]), 1)
        self.assertEqual(len(response.data["errors"]), 1)
