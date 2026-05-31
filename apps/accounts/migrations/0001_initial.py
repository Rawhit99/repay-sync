from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="User",
            fields=[
                ("password", models.CharField(max_length=128, verbose_name="password")),
                ("last_login", models.DateTimeField(blank=True, null=True, verbose_name="last login")),
                ("is_superuser", models.BooleanField(default=False)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("email", models.EmailField(max_length=254, unique=True)),
                ("full_name", models.CharField(max_length=255)),
                ("team", models.CharField(choices=[("FIELD", "Field"), ("CALLING", "Calling")], max_length=20)),
                ("role", models.CharField(
                    choices=[
                        ("COLLECTION_OFFICER", "Collection Officer"),
                        ("MANAGER", "Manager"),
                        ("SENIOR_MANAGER", "Senior Manager"),
                        ("CALLING_AGENT", "Calling Agent"),
                    ],
                    max_length=30,
                )),
                ("is_active", models.BooleanField(default=True)),
                ("is_staff", models.BooleanField(default=False)),
                ("date_joined", models.DateTimeField(default=django.utils.timezone.now)),
                ("reports_to", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name="direct_reports", to="accounts.user",
                )),
                ("groups", models.ManyToManyField(blank=True, related_name="user_set", to="auth.group")),
                ("user_permissions", models.ManyToManyField(blank=True, related_name="user_set", to="auth.permission")),
            ],
            options={"db_table": "users", "ordering": ["email"]},
        ),
    ]
