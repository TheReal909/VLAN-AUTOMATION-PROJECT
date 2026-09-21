from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from inventory.models import ValidatedModel


class VlanChangeLog(ValidatedModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        APPLIED = "APPLIED", "Applied"
        FAILED = "FAILED", "Failed"

    requested_by = models.ForeignKey("auth.User", on_delete=models.PROTECT)
    switch = models.ForeignKey("inventory.Switch", on_delete=models.PROTECT)
    interface_name = models.CharField(max_length=20)
    mac_address = models.CharField(max_length=17)
    previous_vlan = models.ForeignKey("inventory.VlanProfile", related_name="+", on_delete=models.PROTECT)
    requested_vlan = models.ForeignKey("inventory.VlanProfile", related_name="+", on_delete=models.PROTECT)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    approved_by = models.ForeignKey(
        "auth.User", null=True, blank=True, on_delete=models.PROTECT, related_name="approved_vlan_changes"
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    source_ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    applied_at = models.DateTimeField(null=True, blank=True)

    def clean(self):
        super().clean()
        if self.requested_vlan_id and self.requested_vlan.facility_id != self.switch.facility_id:
            raise ValidationError({"requested_vlan": "This VLAN profile isn't provisioned at this switch's facility."})
        if self.requested_vlan_id and not self.requested_vlan.is_manually_changeable:
            raise ValidationError({"requested_vlan": "This VLAN is not enabled for helpdesk-initiated changes."})

    def approve(self, user):
        if self.status != self.Status.PENDING:
            raise ValidationError("Only pending VLAN changes can be approved.")
        self.status = self.Status.APPROVED
        self.approved_by = user
        self.approved_at = timezone.now()

    def __str__(self):
        return f"{self.mac_address}: {self.previous_vlan} -> {self.requested_vlan} ({self.status})"