from django.conf import settings
from django.db import migrations, models
import django.utils.timezone
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AuditLog",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("action", models.CharField(choices=[
                    ("CREATE", "Create"), ("READ", "Read"), ("UPDATE", "Update"),
                    ("DELETE", "Delete"), ("BULK_UPLOAD", "Bulk Upload"), ("LOGIN", "Login"),
                ], max_length=20)),
                ("resource_type", models.CharField(blank=True, max_length=100)),
                ("resource_id", models.CharField(blank=True, max_length=100)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("request_method", models.CharField(blank=True, max_length=10)),
                ("request_path", models.CharField(blank=True, max_length=500)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="audit_logs", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "audit_logs", "ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="auditlog",
            index=models.Index(fields=["-created_at"], name="auditlog_created_at_idx"),
        ),
        migrations.AddIndex(
            model_name="auditlog",
            index=models.Index(fields=["actor", "-created_at"], name="auditlog_actor_created_idx"),
        ),
        migrations.AddIndex(
            model_name="auditlog",
            index=models.Index(fields=["resource_type", "resource_id"], name="auditlog_resource_idx"),
        ),
    ]
