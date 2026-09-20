from django import forms
from django.db.models import Q

from inventory.models import VlanProfile


class VlanChangeRequestForm(forms.Form):
    requested_vlan = forms.ModelChoiceField(
        queryset=VlanProfile.objects.none(),
        label="Target VLAN",
        empty_label="Select a target VLAN",
    )

    def __init__(self, *args, facility, current_vlan_id, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["requested_vlan"].queryset = VlanProfile.objects.filter(
            facility=facility,
            is_active=True,
        ).filter(
            Q(assignment_mode=VlanProfile.AssignmentMode.STATIC, allow_helpdesk_port_change=True)
            | Q(vlan_id=1, allow_helpdesk_port_change=True)
        ).order_by("vlan_id")
        self.current_vlan_id = current_vlan_id

    def clean_requested_vlan(self):
        requested_vlan = self.cleaned_data["requested_vlan"]
        if requested_vlan.vlan_id == self.current_vlan_id:
            raise forms.ValidationError("The port is already assigned to this VLAN.")
        if not requested_vlan.is_manually_changeable:
            raise forms.ValidationError("This VLAN is not available for helpdesk-initiated changes.")
        return requested_vlan
