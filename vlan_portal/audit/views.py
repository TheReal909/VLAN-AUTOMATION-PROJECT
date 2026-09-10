from django.http import HttpResponse


def index(request):
    return HttpResponse("Audit module ready.")
