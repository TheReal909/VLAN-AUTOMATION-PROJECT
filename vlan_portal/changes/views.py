from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from audit.models import AuditLog
from discovery.freshness import is_live_observation_fresh
from discovery.models import PortObservation

from .forms import VlanChangeRequestForm
from .models import VlanChangeLog


@login_required
def request_change(request, observation_id):
    observation = get_object_or_404(
        PortObservation.objects.select_related("switch", "switch__facility"),
        pk=observation_id,
    )
    facility = observation.switch.facility
    if not is_live_observation_fresh(observation):
        return render(
            request,
            "changes/request.html",
            {"observation": observation, "stale_observation": True},
            status=409,
        )
    form = VlanChangeRequestForm(
        request.POST or None,
        facility=facility,
        current_vlan_id=observation.vlan_id,
    )
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            change = VlanChangeLog.objects.create(
                requested_by=request.user,
                switch=observation.switch,
                interface_name=observation.interface_name,
                mac_address=observation.mac_address,
                previous_vlan=observation.vlan_id,
                requested_vlan=form.cleaned_data["requested_vlan"],
            )
            AuditLog.objects.create(
                user=request.user,
                event_type=AuditLog.EventType.VLAN_CHANGE,
                facility_code=observation.switch.facility.code,
                switch=observation.switch,
                mac_address=observation.mac_address,
                source_ip=request.META.get("REMOTE_ADDR"),
                detail={
                    "action": "request_created",
                    "change_id": change.pk,
                    "interface_name": observation.interface_name,
                    "previous_vlan": observation.vlan_id,
                    "requested_vlan": change.requested_vlan.vlan_id,
                    "status": change.status,
                },
            )
        return redirect("changes-requested", observation_id=observation.pk)
    return render(request, "changes/request.html", {"form": form, "observation": observation})


@login_required
def request_created(request, observation_id):
    observation = get_object_or_404(PortObservation, pk=observation_id)
    change = (
        VlanChangeLog.objects.filter(
            requested_by=request.user,
            mac_address=observation.mac_address,
        )
        .select_related("requested_vlan", "switch")
        .first()
    )
    return render(request, "changes/requested.html", {"change": change})
