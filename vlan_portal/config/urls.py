from django.contrib import admin
from django.http import HttpResponse
from django.urls import path


def home(request):
    return HttpResponse("VLAN Automation Portal is ready.")


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", home, name="home"),
]
