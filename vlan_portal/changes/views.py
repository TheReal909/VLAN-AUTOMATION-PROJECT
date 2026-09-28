from django.contrib.auth.decorators import login_required
from django.conf import settings
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
        return redirect("changes-requested", change_id=change.pk)
    return render(request, "changes/request.html", {"form": form, "observation": observation})


@login_required
def request_created(request, change_id):
    change = get_object_or_404(
        VlanChangeLog.objects.select_related("requested_vlan", "switch"),
        pk=change_id,
        requested_by=request.user,
    )
    return render(request, "changes/requested.html", {"change": change, "status_info": _status_info(change)})


@login_required
def my_requests(request):
    changes = list(
        VlanChangeLog.objects.filter(requested_by=request.user)
        .select_related("switch", "requested_vlan")
        .order_by("-created_at")
    )
    for change in changes:
        change.status_info = _status_info(change)
    return render(request, "changes/my_requests.html", {"changes": changes})


def _status_info(change):
    if change.status == VlanChangeLog.Status.PENDING:
        return {"title": "Awaiting engineer approval", "detail": "The switch has not been changed.", "tone": "warning"}
    if change.status == VlanChangeLog.Status.APPROVED:
        if not change.approved_at:
            return {
                "title": "Approval needs review",
                "detail": "No approval timestamp is recorded. Contact network operations; do not assume the switch changed.",
                "tone": "warning",
            }
        if not settings.CHANGE_EXECUTION_ENABLED:
            return {
                "title": "Approved, execution disabled",
                "detail": "Automatic switch changes are disabled. The switch has not been changed by this request.",
                "tone": "warning",
            }
        queued = AuditLog.objects.filter(
            event_type=AuditLog.EventType.VLAN_CHANGE,
            detail__change_id=change.pk,
            detail__action="execution_queued",
        ).exists()
        if queued:
            return {
                "title": "Queued for switch worker",
                "detail": "The request is waiting for or being processed by the VLAN worker.",
                "tone": "info",
            }
        return {
            "title": "Approved, not queued",
            "detail": "No worker queue event is recorded. Contact network operations to check worker and credentials.",
            "tone": "warning",
        }
    if change.status == VlanChangeLog.Status.APPLIED:
        return {"title": "Applied and verified", "detail": "The switch reported the requested VLAN.", "tone": "success"}
    return {
        "title": "Change failed",
        "detail": change.error_message or "The switch change did not complete. Contact network operations.",
        "tone": "error",
    }
