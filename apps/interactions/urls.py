from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.interactions.views import InteractionViewSet
from apps.interactions.views_bulk import InteractionBulkUploadView

router = DefaultRouter()
router.register("", InteractionViewSet, basename="interaction")

urlpatterns = [
    path("bulk-upload/", InteractionBulkUploadView.as_view(), name="interaction-bulk-upload"),
    path("", include(router.urls)),
]
