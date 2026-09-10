from django.db import models


class PortObservation(models.Model):
    mac_address = models.CharField(max_length=17, unique=True, db_index=True)
    switch = models.ForeignKey("inventory.Switch", on_delete=models.CASCADE, related_name="port_observations")
    interface_name = models.CharField(max_length=20)
    vlan_id = models.PositiveSmallIntegerField(help_text="Raw VLAN ID as reported by the switch.")
    observed_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-observed_at"]

    def __str__(self):
        return f"{self.mac_address} @ {self.switch} {self.interface_name} (VLAN {self.vlan_id})"