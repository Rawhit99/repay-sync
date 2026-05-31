from django.urls import path

from apps.accounts.views import MeView
from apps.accounts.views_bulk import UserBulkUploadView

urlpatterns = [
    path("me/", MeView.as_view(), name="user-me"),
    path("bulk-upload/", UserBulkUploadView.as_view(), name="user-bulk-upload"),
]
