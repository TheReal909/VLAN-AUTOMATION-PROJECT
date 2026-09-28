from django import forms

from discovery.parsers import normalize_mac
from inventory.models import Facility


class MacLookupForm(forms.Form):
    facility = forms.ModelChoiceField(
        queryset=Facility.objects.filter(is_active=True),
        empty_label="Select a facility",
    )
    mac_address = forms.CharField(
        max_length=17,
        label="MAC address",
        help_text="Example: A83C.A534.A128",
    )

    def clean_mac_address(self):
        value = self.cleaned_data["mac_address"].strip()
        try:
            return normalize_mac(value)
        except ValueError as exc:
            raise forms.ValidationError("Enter a valid 12-digit MAC address.") from exc
