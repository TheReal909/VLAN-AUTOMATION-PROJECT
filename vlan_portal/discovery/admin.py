from django.contrib import admin

from .models import PortObservation


@admin.register(PortObservation)
class PortObservationAdmin(admin.ModelAdmin):
	list_display = ("mac_address", "switch", "interface_name", "vlan_id", "observed_at")
	list_filter = ("switch", "vlan_id")
	search_fields = ("mac_address", "interface_name", "switch__name", "switch__hostname")
	autocomplete_fields = ("switch",)
