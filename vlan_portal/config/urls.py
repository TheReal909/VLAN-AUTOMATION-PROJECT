from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.urls import include, path

from changes.views import request_change, request_created
from discovery.views import index as discovery_index


@login_required
def home(request):
    from audit.models import AuditLog
    from changes.models import VlanChangeLog
    from discovery.models import PortObservation
    from inventory.models import Facility, Switch

    context = {
        "facility_count": Facility.objects.filter(is_active=True).count(),
        "switch_count": Switch.objects.filter(is_active=True).count(),
        "observation_count": PortObservation.objects.count(),
        "pending_change_count": VlanChangeLog.objects.filter(
            status=VlanChangeLog.Status.PENDING
        ).count(),
        "recent_audits": AuditLog.objects.select_related("user", "switch")[:5],
    }
    return render(request, "home.html", context)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("changes/request/<int:observation_id>/", request_change, name="changes-request"),
    path("changes/requested/<int:observation_id>/", request_created, name="changes-requested"),
    path("discovery/", discovery_index, name="discovery"),
    path("", home, name="home"),
]
