from django.urls import path

from .views import request_change, request_created

urlpatterns = [
    path("request/<int:observation_id>/", request_change, name="changes-request"),
    path("requested/<int:observation_id>/", request_created, name="changes-requested"),
]
