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

    def test_cacheable(self):
        req = HttpRequest()
        req.path = "/some/path"
        req.method = "GET"
        self.assertTrue(request_is_cacheable(req))

        # TODO: ensure that messages works

        res = HttpResponse("fun times")
        self.assertTrue(response_is_cacheable(req, res))

        redirect = HttpResponseRedirect("someurl")
        self.assertFalse(response_is_cacheable(req, redirect))

        res['Pragma'] = "no-cache"
        self.assertFalse(response_is_cacheable(req, res))

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
