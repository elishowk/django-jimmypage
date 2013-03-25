from django.http import HttpResponse
from django.contrib import messages
from jimmypage import cache_page

@cache_page
def index(request):
    return HttpResponse("foo")

@cache_page
def test_messages(request):
    messages.info(request, "added an info message")
    return HttpResponse("added an info message")

@cache_page
def test_text_plain(request):
    return HttpResponse("text/plain", mimetype="text/plain")

@cache_page
def test_text_html(request):
    return HttpResponse("<b>text/html</b>", mimetype="text/html")
