from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Customer",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("external_id", models.CharField(max_length=100, unique=True)),
                ("name", models.CharField(blank=True, max_length=255)),
                ("phone", models.CharField(blank=True, max_length=50)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "customers", "ordering": ["external_id"]},
        ),
        migrations.CreateModel(
            name="CustomerAssignment",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("assigned_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("customer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="assignments", to="customers.customer")),
                ("officer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="customer_assignments", to="accounts.user")),
            ],
            options={"db_table": "customer_assignments"},
        ),
        migrations.AddConstraint(
            model_name="customerassignment",
            constraint=models.UniqueConstraint(fields=("customer",), name="unique_active_customer_assignment"),
        ),
    ]
