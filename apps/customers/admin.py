from django.contrib import admin

from apps.customers.models import Customer, CustomerAssignment


class CustomerAssignmentInline(admin.TabularInline):
    model = CustomerAssignment
    extra = 0
    raw_id_fields = ("officer",)


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("external_id", "name", "phone", "created_at")
    search_fields = ("external_id", "name", "phone")
    inlines = [CustomerAssignmentInline]


@admin.register(CustomerAssignment)
class CustomerAssignmentAdmin(admin.ModelAdmin):
    list_display = ("customer", "officer", "assigned_at")
    raw_id_fields = ("customer", "officer")
