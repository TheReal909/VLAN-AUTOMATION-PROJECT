from django.contrib import admin
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction

from audit.models import AuditLog

from .models import VlanChangeLog


@admin.register(VlanChangeLog)
class VlanChangeLogAdmin(admin.ModelAdmin):
	list_display = ("mac_address", "switch", "interface_name", "previous_vlan", "requested_vlan", "status", "created_at")
	list_filter = ("status", "switch__facility", "created_at")
	search_fields = ("mac_address", "interface_name", "switch__name", "requested_by__username")
	autocomplete_fields = ("requested_by", "switch", "previous_vlan", "requested_vlan")
	readonly_fields = ("created_at", "approved_at", "applied_at")
	actions = ("approve_requests",)

	@admin.action(description="Approve selected pending VLAN changes")
	def approve_requests(self, request, queryset):
		approved = 0
		for change in queryset.select_related("switch", "requested_vlan", "previous_vlan"):
			if change.status != VlanChangeLog.Status.PENDING:
				continue
			try:
				with transaction.atomic():
					change.approve(request.user)
					change.save(update_fields=["status", "approved_by", "approved_at"])
					AuditLog.objects.create(
						user=request.user,
						event_type=AuditLog.EventType.VLAN_CHANGE,
						facility_code=change.switch.facility.code,
						switch=change.switch,
						mac_address=change.mac_address,
						detail={
							"action": "request_approved",
							"change_id": change.pk,
							"requested_vlan": change.requested_vlan.vlan_id,
							"approved_by": request.user.username,
						},
					)
			except ValidationError as exc:
				self.message_user(request, str(exc), messages.ERROR)
				continue
			approved += 1
		self.message_user(request, f"Approved {approved} VLAN change(s).", messages.SUCCESS)
