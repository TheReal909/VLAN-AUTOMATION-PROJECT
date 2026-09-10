from django.db import models


class AuditLog(models.Model):
    class EventType(models.TextChoices):
        LOOKUP = "LOOKUP", "Lookup"
        VLAN_CHANGE = "VLAN_CHANGE", "VLAN change"
        LOGIN = "LOGIN", "Login"

    user = models.ForeignKey("auth.User", on_delete=models.PROTECT)
    event_type = models.CharField(max_length=20, choices=EventType.choices)
    facility_code = models.CharField(max_length=6, blank=True)
    switch = models.ForeignKey("inventory.Switch", null=True, on_delete=models.SET_NULL)
    mac_address = models.CharField(max_length=17, blank=True)
    detail = models.JSONField(default=dict, blank=True)
    source_ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M} {self.user} {self.event_type}"