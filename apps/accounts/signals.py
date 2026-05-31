from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.accounts.models import User
from apps.common.hierarchy import invalidate_reporting_tree_cache


@receiver([post_save, post_delete], sender=User)
def invalidate_hierarchy_cache_on_user_change(sender, instance, **kwargs):
    invalidate_reporting_tree_cache()
