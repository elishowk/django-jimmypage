from django.http import HttpResponse
from django.contrib import messages

def index(request):
    return HttpResponse("foo")

def test_messages(request):
    messages.info(request, "added an info message")
    return HttpResponse("added an info message")
