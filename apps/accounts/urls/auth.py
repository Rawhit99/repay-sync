from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from apps.accounts.auth import AuditedTokenObtainPairView

urlpatterns = [
    path("token/", AuditedTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]
