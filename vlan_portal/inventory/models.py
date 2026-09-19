from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models


class ValidatedModel(models.Model):
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class Facility(ValidatedModel):
    code = models.CharField(
        max_length=6,
        unique=True,
        validators=[RegexValidator(regex=r"^F\d{5}$", message="Facility code must be F followed by exactly five digits, such as F19114.")],
        help_text="Example: F19114",
    )
    name = models.CharField(max_length=150, help_text="Friendly name shown to helpdesk users.")
    address = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]

    def save(self, *args, **kwargs):
        self.code = self.code.upper().strip()
        self.name = self.name.strip()
        super().save(*args, **kwargs)

    @property
    def active_switch_count(self):
        return self.switches.filter(is_active=True).count()

    def __str__(self):
        return f"{self.code} — {self.name}"


class Switch(ValidatedModel):
    class ClosetRole(models.TextChoices):
        MDF = "mdf", "MDF"
        IDF = "idf", "IDF"

    class ModelFamily(models.TextChoices):
        ICX_7150 = "ICX7150", "ICX 7150"
        ICX_7250 = "ICX7250", "ICX 7250"
        ICX_8200 = "ICX8200", "ICX 8200"

    facility = models.ForeignKey(Facility, on_delete=models.PROTECT, related_name="switches")
    name = models.CharField(max_length=100, help_text="Friendly inventory name, e.g. MDF-STACK-01.")
    hostname = models.CharField(max_length=255, unique=True, help_text="DNS name, for reference only.")
    management_ip = models.GenericIPAddressField(unique=True, help_text="IP the automation connects to.")
    closet_role = models.CharField(max_length=3, choices=ClosetRole.choices)
    upstream_switch = models.ForeignKey(
        "self", on_delete=models.PROTECT, related_name="downstream_switches", null=True, blank=True,
        help_text="Direct upstream managed logical switch; may be an MDF or another IDF.",
    )
    model_family = models.CharField(max_length=20, choices=ModelFamily.choices)
    fastiron_version = models.CharField(max_length=80, blank=True, help_text="Example: 10.0.10")
    location_note = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["facility__code", "closet_role", "name"]
        constraints = [models.UniqueConstraint(fields=["facility", "name"], name="unique_switch_name_per_facility")]

    def clean(self):
        super().clean()
        if self.upstream_switch and self.upstream_switch == self:
            raise ValidationError({"upstream_switch": "A switch cannot be its own upstream switch."})
        if self.upstream_switch and self.upstream_switch.facility_id != self.facility_id:
            raise ValidationError({"upstream_switch": "The upstream switch must be in the same facility."})
        if self.closet_role == self.ClosetRole.MDF and self.upstream_switch:
            raise ValidationError({"upstream_switch": "An MDF switch should not have an upstream switch."})
        if self.upstream_switch:
            seen_switches = {self.pk if self.pk is not None else id(self)}
            upstream_switch = self.upstream_switch
            while upstream_switch:
                switch_key = upstream_switch.pk if upstream_switch.pk is not None else id(upstream_switch)
                if switch_key in seen_switches:
                    raise ValidationError({"upstream_switch": "The upstream switch hierarchy cannot contain a cycle."})
                seen_switches.add(switch_key)
                if upstream_switch.facility_id != self.facility_id:
                    raise ValidationError({"upstream_switch": "The upstream switch must be in the same facility."})
                upstream_switch = upstream_switch.upstream_switch

    def save(self, *args, **kwargs):
        self.hostname = self.hostname.lower().strip()
        self.name = self.name.strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.facility.code} — {self.name} ({self.hostname})"


class VlanProfile(ValidatedModel):
    class AssignmentMode(models.TextChoices):
        STATIC = "static", "Static / manually managed"
        POLICY_CONTROLLED = "policy_controlled", "Policy-controlled (802.1X/RADIUS)"

    facility = models.ForeignKey(Facility, on_delete=models.PROTECT, related_name="vlan_profiles")
    label = models.CharField(max_length=80, help_text="Helpdesk-facing name, e.g. Guest or Vendor.")
    vlan_id = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(4094)])
    assignment_mode = models.CharField(max_length=25, choices=AssignmentMode.choices, default=AssignmentMode.STATIC)
    requester_ad_group = models.CharField(max_length=255, help_text="Exact AD security-group name.")
    allow_helpdesk_port_change = models.BooleanField(default=False)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["facility__code", "label"]
        constraints = [models.UniqueConstraint(fields=["facility", "label"], name="unique_vlan_profile_label_per_facility")]
        indexes = [models.Index(fields=["facility", "is_active"])]

    def clean(self):
        super().clean()
        if (
            self.assignment_mode == self.AssignmentMode.POLICY_CONTROLLED
            and self.allow_helpdesk_port_change
            and self.vlan_id != 1
        ):
            raise ValidationError({"allow_helpdesk_port_change": "Policy-controlled VLANs cannot be changed manually by helpdesk."})

    def save(self, *args, **kwargs):
        self.label = self.label.strip()
        self.requester_ad_group = self.requester_ad_group.strip()
        super().save(*args, **kwargs)

    @property
    def is_manually_changeable(self):
        return self.is_active and self.allow_helpdesk_port_change and (
            self.assignment_mode == self.AssignmentMode.STATIC or self.vlan_id == 1
        )

    def __str__(self):
        return f"{self.facility.code}: {self.label} (VLAN {self.vlan_id})"