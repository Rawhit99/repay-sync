from django.contrib import admin

from apps.interactions.models import Interaction


@admin.register(Interaction)
class InteractionAdmin(admin.ModelAdmin):
    list_display = ("customer", "created_by", "disposition", "contacted_at")
    list_filter = ("disposition",)
    raw_id_fields = ("customer", "created_by")
    search_fields = ("customer__external_id", "notes")
