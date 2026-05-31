from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("accounts", "0001_initial"),
        ("customers", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Interaction",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("disposition", models.CharField(choices=[
                    ("CONTACTED", "Contacted"), ("NO_ANSWER", "No Answer"),
                    ("PROMISE_TO_PAY", "Promise to Pay"), ("REFUSED", "Refused"),
                    ("WRONG_NUMBER", "Wrong Number"), ("CALLBACK_REQUESTED", "Callback Requested"),
                ], max_length=30)),
                ("notes", models.TextField(blank=True)),
                ("contacted_at", models.DateTimeField()),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="interactions", to="accounts.user")),
                ("customer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="interactions", to="customers.customer")),
            ],
            options={"db_table": "interactions", "ordering": ["-contacted_at"]},
        ),
        migrations.AddIndex(
            model_name="interaction",
            index=models.Index(fields=["customer", "-contacted_at"], name="interaction_customer_contacted_idx"),
        ),
    ]
