from django.contrib import admin

from .models import Facility, Switch, VlanProfile


@admin.register(Facility)
class FacilityAdmin(admin.ModelAdmin):
	list_display = ("code", "name", "is_active", "active_switch_count")
	list_filter = ("is_active",)
	search_fields = ("code", "name", "address")


@admin.register(Switch)
class SwitchAdmin(admin.ModelAdmin):
	list_display = ("name", "facility", "closet_role", "upstream_switch", "management_ip", "is_active")
	list_filter = ("facility", "closet_role", "model_family", "is_active")
	search_fields = ("name", "hostname", "management_ip")
	autocomplete_fields = ("facility", "upstream_switch")


@admin.register(VlanProfile)
class VlanProfileAdmin(admin.ModelAdmin):
	list_display = ("label", "facility", "vlan_id", "assignment_mode", "allow_helpdesk_port_change", "is_active")
	list_filter = ("facility", "assignment_mode", "allow_helpdesk_port_change", "is_active")
	search_fields = ("label", "requester_ad_group", "description")
	autocomplete_fields = ("facility",)
