from django.urls import include, path

urlpatterns = [
    path("auth/", include("apps.accounts.urls.auth")),
    path("users/", include("apps.accounts.urls.users")),
    path("customers/", include("apps.customers.urls")),
    path("interactions/", include("apps.interactions.urls")),
    path("audit-logs/", include("apps.audit.urls")),
]
