from django.conf import settings
from django.shortcuts import render

from .connectors import DiscoveryError, MacDiscoveryService, NetmikoReadOnlyConnector
from .forms import MacLookupForm
from .models import PortObservation


def index(request):
    form = MacLookupForm(request.POST or request.GET or None)
    observation = None
    live_result = None
    live_error = None
    searched = bool(request.GET or request.POST)
    if form.is_valid():
        observation = (
            PortObservation.objects.select_related("switch", "switch__facility")
            .filter(
                switch__facility=form.cleaned_data["facility"],
                mac_address__iexact=form.cleaned_data["mac_address"],
            )
            .first()
        )
        if request.method == "POST" and request.POST.get("action") == "live-discovery":
            if not settings.DISCOVERY_SSH_USERNAME or not settings.DISCOVERY_SSH_PASSWORD:
                live_error = "Live discovery is not configured with SSH credentials."
            else:
                connector = NetmikoReadOnlyConnector(
                    settings.DISCOVERY_SSH_USERNAME,
                    settings.DISCOVERY_SSH_PASSWORD,
                    port=settings.DISCOVERY_SSH_PORT,
                    timeout=settings.DISCOVERY_SSH_TIMEOUT,
                )
                try:
                    live_result = MacDiscoveryService(connector).locate(
                        form.cleaned_data["facility"], form.cleaned_data["mac_address"]
                    )
                    observation, _ = PortObservation.objects.update_or_create(
                        mac_address=live_result.mac_address,
                        defaults={
                            "switch": live_result.switch,
                            "interface_name": live_result.entry.interface_name,
                            "vlan_id": live_result.entry.vlan_id,
                        },
                    )
                except DiscoveryError as exc:
                    live_error = str(exc)
    return render(
        request,
        "discovery/lookup.html",
        {
            "form": form,
            "observation": observation,
            "live_result": live_result,
            "live_error": live_error,
            "searched": searched,
        },
    )
