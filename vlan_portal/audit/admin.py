from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
	list_display = ("created_at", "event_type", "user", "facility_code", "switch", "mac_address")
	list_filter = ("event_type", "created_at")
	search_fields = ("facility_code", "mac_address", "user__username", "switch__name")
	autocomplete_fields = ("user", "switch")
	readonly_fields = ("created_at",)
