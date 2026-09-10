from django.contrib import admin

from .models import VlanChangeLog


@admin.register(VlanChangeLog)
class VlanChangeLogAdmin(admin.ModelAdmin):
	list_display = ("mac_address", "switch", "interface_name", "previous_vlan", "requested_vlan", "status", "created_at")
	list_filter = ("status", "switch__facility", "created_at")
	search_fields = ("mac_address", "interface_name", "switch__name", "requested_by__username")
	autocomplete_fields = ("requested_by", "switch", "previous_vlan", "requested_vlan")
	readonly_fields = ("created_at", "applied_at")
