import re

from django import forms

from inventory.models import Facility


class MacLookupForm(forms.Form):
    facility = forms.ModelChoiceField(
        queryset=Facility.objects.filter(is_active=True),
        empty_label="Select a facility",
    )
    mac_address = forms.CharField(
        max_length=17,
        label="MAC address",
        help_text="Example: 02:00:00:00:00:01",
    )

    def clean_mac_address(self):
        value = self.cleaned_data["mac_address"].strip()
        compact = re.sub(r"[:-]", "", value)
        if not re.fullmatch(r"[0-9a-fA-F]{12}", compact):
            raise forms.ValidationError("Enter a valid 12-digit MAC address.")
        return ":".join(compact[index:index + 2] for index in range(0, 12, 2)).lower()
