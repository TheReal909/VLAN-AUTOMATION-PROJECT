from django.contrib import admin
from django.http import HttpResponse
from django.urls import path

from changes.views import request_change, request_created
from discovery.views import index as discovery_index


def home(request):
    return HttpResponse("VLAN Automation Portal is ready.")


urlpatterns = [
    path("admin/", admin.site.urls),
    path("changes/request/<int:observation_id>/", request_change, name="changes-request"),
    path("changes/requested/<int:observation_id>/", request_created, name="changes-requested"),
    path("discovery/", discovery_index, name="discovery"),
    path("", home, name="home"),
]
