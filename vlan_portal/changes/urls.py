from django.urls import path

from .views import my_requests, request_change, request_created

urlpatterns = [
    path("mine/", my_requests, name="changes-mine"),
    path("request/<int:observation_id>/", request_change, name="changes-request"),
    path("requested/<int:change_id>/", request_created, name="changes-requested"),
]
