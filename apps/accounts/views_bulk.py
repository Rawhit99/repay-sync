from apps.accounts.permissions import IsManagerOrSuperuser
from apps.accounts.services.bulk_users import bulk_create_users_from_csv
from apps.common.views import BaseBulkUploadView


class UserBulkUploadView(BaseBulkUploadView):
    permission_classes = [IsManagerOrSuperuser]
    audit_resource_type = "user"

    def process_upload(self, content, user):
        return bulk_create_users_from_csv(content)
