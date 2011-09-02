from django.test import TestCase
from django.test.client import RequestFactory

from django.contrib.auth.models import User, AnonymousUser
from django.contrib import messages
from django.db import models
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.contrib.auth import login

from jimmypage.cache import request_is_cacheable, response_is_cacheable, get_cache_key

class CacheabilityTest(TestCase):
    urls = 'jimmypage.test_urls'

    def setUp(self):
        self.factory = RequestFactory()

    def test_only_cache_get_requests(self):
        request = self.factory.get("/")
        self.assertTrue(request_is_cacheable(request))

        request = self.factory.post("/")
        self.assertFalse(request_is_cacheable(request))

    def test_authenticated_and_anonymous_users(self):
        request = self.factory.get("/")
        request.user = AnonymousUser()
        self.assertTrue(request_is_cacheable(request))

        john = User.objects.create_user("john", "john@example.com", "secret")
        self.client.login(username="john", password="secret")
        response = self.client.get("/")
        self.assertTrue(request_is_cacheable(request))

    def test_cache_simple_responses(self):
        request = self.factory.get("/")
        response = HttpResponse("foo")
        self.assertTrue(response_is_cacheable(request, response))

    def test_dont_cache_responses_that_include_messages(self):
        request = self.factory.get("/")
        response = self.client.get("/test_messages/")
        self.assertFalse(response_is_cacheable(request, response))

    def test_dont_cache_redirects(self):
        request = self.factory.get("/")
        response = HttpResponseRedirect("/other/")
        self.assertFalse(response_is_cacheable(request, response))

    def test_dont_cache_if_pragma_says_so(self):
        request = self.factory.get("/")
        response = HttpResponse()
        response['Pragma'] = "no-cache"
        self.assertFalse(response_is_cacheable(request, response))

    def test_dont_cache_if_vary_is_cookie(self):
        request = self.factory.get("/")
        response = HttpResponse()
        response['Vary'] = "Cookie"
        self.assertFalse(response_is_cacheable(request, response))

    def test_key_uniqueness(self):
        req = HttpRequest()
        req.path = "/some/path"
        req.method = "GET"
        req.user = AnonymousUser()

        req2 = HttpRequest()
        req2.path = "/some/path"
        req2.method = "GET"
        req2.user = User.objects.create(username="a_user")

        req3 = HttpRequest()
        req3.path = "/some/other/path"
        req3.method = "GET"
        req3.user = AnonymousUser()

        self.assertNotEqual(get_cache_key(req), get_cache_key(req2))
        self.assertNotEqual(get_cache_key(req), get_cache_key(req3))
