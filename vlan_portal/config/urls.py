from django.contrib import admin
from django.http import HttpResponse
from django.urls import path

from discovery.views import index as discovery_index


def home(request):
    return HttpResponse("VLAN Automation Portal is ready.")


urlpatterns = [
    path("admin/", admin.site.urls),
    path("discovery/", discovery_index, name="discovery"),
    path("", home, name="home"),
]
