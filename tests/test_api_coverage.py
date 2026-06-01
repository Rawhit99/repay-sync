"""Comprehensive API coverage."""
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Role, Team, User
from apps.audit.models import AuditLog
from apps.common.exceptions import ErrorCode
from apps.customers.models import Customer, CustomerAssignment
from apps.interactions.models import Disposition, Interaction


def csv_upload(name: str, content: str) -> SimpleUploadedFile:
    return SimpleUploadedFile(name, content.encode("utf-8"), content_type="text/csv")


class BaseTestCase(TestCase):
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
        self.customer_a = Customer.objects.create(external_id="CUST-A", name="Alpha", phone="+1")
        self.customer_b = Customer.objects.create(external_id="CUST-B", name="Beta", phone="+2")
        CustomerAssignment.objects.create(customer=self.customer_a, officer=self.officer)
        CustomerAssignment.objects.create(customer=self.customer_b, officer=self.other_officer)

    def auth(self, user):
        self.client.force_authenticate(user=user)


class AuthEndpointTests(BaseTestCase):
    def test_token_invalid_credentials(self):
        response = self.client.post(
            "/api/v1/auth/token/",
            {"email": "agent@example.com", "password": "wrong"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_refresh(self):
        token = self.client.post(
            "/api/v1/auth/token/",
            {"email": "agent@example.com", "password": "pass123456"},
            format="json",
        ).data
        response = self.client.post(
            "/api/v1/auth/token/refresh/",
            {"refresh": token["refresh"]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_unauthenticated_request_rejected(self):
        response = self.client.get("/api/v1/customers/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class UserEndpointTests(BaseTestCase):
    def test_me_returns_profile(self):
        self.auth(self.officer)
        response = self.client.get("/api/v1/users/me/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "officer@example.com")
        self.assertEqual(response.data["team"], Team.FIELD)

    def test_senior_can_bulk_upload_users(self):
        self.auth(self.senior)
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
        self.assertIn("password", response.data["created"][0])


class CustomerEndpointTests(BaseTestCase):
    def test_senior_sees_subtree_customers(self):
        self.auth(self.senior)
        response = self.client.get("/api/v1/customers/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)

    def test_officer_sees_only_assigned(self):
        self.auth(self.officer)
        response = self.client.get("/api/v1/customers/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["external_id"], "CUST-A")

    def test_customer_detail_includes_assigned_officer(self):
        self.auth(self.officer)
        response = self.client.get(f"/api/v1/customers/{self.customer_a.pk}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["assigned_officer"]["email"], "officer@example.com")

    def test_manager_can_create_customer(self):
        self.auth(self.manager)
        response = self.client.post(
            "/api/v1/customers/",
            {
                "external_id": "CUST-NEW",
                "name": "New Co",
                "phone": "+99",
                "assigned_officer_email": "officer@example.com",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Customer.objects.filter(external_id="CUST-NEW").exists())

    def test_calling_agent_can_create_customer(self):
        self.auth(self.agent)
        response = self.client.post(
            "/api/v1/customers/",
            {"external_id": "CUST-CALL", "name": "Call Co"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_manager_can_assign_customer_to_officer(self):
        unassigned = Customer.objects.create(external_id="CUST-UNASSIGNED", name="Unassigned")
        self.auth(self.manager)
        response = self.client.patch(
            f"/api/v1/customers/{unassigned.pk}/assign/",
            {"assigned_officer_email": "officer@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["assigned_officer"]["email"], "officer@example.com")
        self.assertTrue(
            CustomerAssignment.objects.filter(
                customer=unassigned, officer=self.officer
            ).exists()
        )

    def test_manager_can_reassign_customer(self):
        self.auth(self.manager)
        response = self.client.patch(
            f"/api/v1/customers/{self.customer_b.pk}/assign/",
            {"assigned_officer_email": "officer@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        assignment = CustomerAssignment.objects.get(customer=self.customer_b)
        self.assertEqual(assignment.officer_id, self.officer.pk)

    def test_officer_cannot_assign_customer(self):
        self.auth(self.officer)
        response = self.client.patch(
            f"/api/v1/customers/{self.customer_a.pk}/assign/",
            {"assigned_officer_email": "other@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_officer_cannot_create_customer(self):
        self.auth(self.officer)
        response = self.client.post(
            "/api/v1/customers/",
            {"external_id": "CUST-X", "name": "Denied"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_duplicate_external_id_rejected(self):
        self.auth(self.manager)
        response = self.client.post(
            "/api/v1/customers/",
            {"external_id": "CUST-A", "name": "Dup"},
            format="json",
        )
        self.assertIn(response.status_code, (status.HTTP_400_BAD_REQUEST, status.HTTP_409_CONFLICT))
        self.assertIn(
            response.data["error"]["code"],
            (ErrorCode.CONFLICT, ErrorCode.DUPLICATE_RESOURCE, ErrorCode.VALIDATION_ERROR),
        )

    def test_interaction_history_ordered_newest_first(self):
        Interaction.objects.create(
            customer=self.customer_a,
            created_by=self.officer,
            disposition=Disposition.NO_ANSWER,
            notes="Old",
            contacted_at=timezone.now() - timezone.timedelta(days=1),
        )
        Interaction.objects.create(
            customer=self.customer_a,
            created_by=self.agent,
            disposition=Disposition.CONTACTED,
            notes="New",
            contacted_at=timezone.now(),
        )
        self.auth(self.officer)
        response = self.client.get(f"/api/v1/customers/{self.customer_a.pk}/interactions/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"]
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["disposition"], Disposition.CONTACTED)


class InteractionEndpointTests(BaseTestCase):
    def test_create_interaction_success(self):
        self.auth(self.officer)
        response = self.client.post(
            "/api/v1/interactions/",
            {
                "customer": str(self.customer_a.pk),
                "disposition": Disposition.PROMISE_TO_PAY,
                "notes": "Agreed to pay",
                "contacted_at": "2026-05-30T10:00:00Z",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["disposition"], Disposition.PROMISE_TO_PAY)
        self.assertTrue(Interaction.objects.filter(customer=self.customer_a, notes="Agreed to pay").exists())

    def test_create_interaction_access_denied(self):
        self.auth(self.officer)
        response = self.client.post(
            "/api/v1/interactions/",
            {
                "customer": str(self.customer_b.pk),
                "disposition": Disposition.CONTACTED,
                "notes": "Denied",
                "contacted_at": "2026-05-30T10:00:00Z",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["error"]["code"], ErrorCode.CUSTOMER_ACCESS_DENIED)

    def test_retrieve_interaction(self):
        interaction = Interaction.objects.create(
            customer=self.customer_a,
            created_by=self.officer,
            disposition=Disposition.CONTACTED,
            notes="Test",
            contacted_at=timezone.now(),
        )
        self.auth(self.officer)
        response = self.client.get(f"/api/v1/interactions/{interaction.pk}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["customer_external_id"], "CUST-A")

    def test_officer_cannot_patch_unassigned_interaction(self):
        interaction = Interaction.objects.create(
            customer=self.customer_b,
            created_by=self.other_officer,
            disposition=Disposition.CONTACTED,
            notes="Other",
            contacted_at=timezone.now(),
        )
        self.auth(self.officer)
        response = self.client.patch(
            f"/api/v1/interactions/{interaction.pk}/",
            {"notes": "Should fail"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_agent_can_update_any_interaction(self):
        interaction = Interaction.objects.create(
            customer=self.customer_b,
            created_by=self.other_officer,
            disposition=Disposition.CONTACTED,
            notes="Before",
            contacted_at=timezone.now(),
        )
        self.auth(self.agent)
        response = self.client.patch(
            f"/api/v1/interactions/{interaction.pk}/",
            {"notes": "After"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class BulkUploadEdgeTests(BaseTestCase):
    def test_bulk_users_all_invalid_returns_400(self):
        self.auth(self.senior)
        csv_content = (
            "email,full_name,team,role,manager_email\n"
            "officer@example.com,Duplicate,FIELD,COLLECTION_OFFICER,manager@example.com\n"
        )
        response = self.client.post(
            "/api/v1/users/bulk-upload/",
            {"file": csv_upload("users.csv", csv_content)},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(len(response.data["errors"]), 1)

    def test_bulk_interactions_invalid_customer(self):
        self.auth(self.agent)
        csv_content = (
            "customer_external_id,user_email,disposition,notes,contacted_at\n"
            "NO-SUCH,agent@example.com,CONTACTED,Missing customer,2026-05-28T10:30:00Z\n"
        )
        response = self.client.post(
            "/api/v1/interactions/bulk-upload/",
            {"file": csv_upload("interactions.csv", csv_content)},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class AuditEndpointTests(BaseTestCase):
    def test_manager_can_list_audit_logs(self):
        self.auth(self.manager)
        response = self.client.get("/api/v1/audit-logs/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_officer_cannot_list_audit_logs(self):
        self.auth(self.officer)
        response = self.client.get("/api/v1/audit-logs/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_login_creates_audit_log(self):
        self.client.post(
            "/api/v1/auth/token/",
            {"email": "agent@example.com", "password": "pass123456"},
            format="json",
        )
        self.assertTrue(AuditLog.objects.filter(action="LOGIN", resource_type="auth").exists())

    def test_customer_read_creates_audit_log(self):
        self.auth(self.officer)
        self.client.get("/api/v1/customers/")
        self.assertTrue(
            AuditLog.objects.filter(action="READ", resource_type="customer", actor=self.officer).exists()
        )
