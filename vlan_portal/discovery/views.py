from django.shortcuts import render

from .forms import MacLookupForm
from .models import PortObservation


def index(request):
    form = MacLookupForm(request.GET or None)
    observation = None
    searched = bool(request.GET)
    if form.is_valid():
        observation = (
            PortObservation.objects.select_related("switch", "switch__facility")
            .filter(
                switch__facility=form.cleaned_data["facility"],
                mac_address__iexact=form.cleaned_data["mac_address"],
            )
            .first()
        )
    return render(
        request,
        "discovery/lookup.html",
        {"form": form, "observation": observation, "searched": searched},
    )
