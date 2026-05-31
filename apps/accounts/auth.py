from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.accounts.models import User
from apps.audit.models import AuditAction
from apps.audit.services import log_audit_event


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = "email"


class AuditedTokenObtainPairView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code != 200:
            return response

        email = request.data.get("email", "")
        user = User.objects.filter(email__iexact=email).only("pk").first()
        log_audit_event(
            actor=user,
            action=AuditAction.LOGIN,
            resource_type="auth",
            resource_id=str(user.pk) if user else "",
            request=request,
            metadata={"email": email},
        )
        return response
