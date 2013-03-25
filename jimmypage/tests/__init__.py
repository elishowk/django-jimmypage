import time

from django.test import TestCase
from django.test.client import RequestFactory

from django.contrib.auth.models import User, AnonymousUser
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.core.cache import cache

from jimmypage.cache import request_is_cacheable, response_is_cacheable, get_cache_key
from jimmypage import cache_page
from jimmypage.tests.views import test_text_plain, test_text_html

from testapp.models import Article


class JimmyPageTestsBase(TestCase):
    urls = 'jimmypage.tests.urls'

    def setUp(self):
        self.factory = RequestFactory()


class JimmyPageCacheTests(JimmyPageTestsBase):
    def get_from_cache(self, request):
        return cache.get(get_cache_key(request))

    def test_serve_correct_content_type_from_cache(self):
        """Ensure each view gets served with its appropriate Content-Type.

        Otherwise, every response gets served as DEFAULT_CONTENT_TYPE which
        would mangle responses that aren't the default Content-Type.
        """
        request = self.factory.get("/content-types/text/plain/")
        response = test_text_plain(request)

        (content, content_type) = self.get_from_cache(request)
        self.assertEqual(content, "text/plain", content)
        self.assertEqual(content_type, "text/plain", content_type)

        response = self.client.get("/content-types/text/plain/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, "text/plain")

        headers = dict(response.items())
        self.assertEqual(headers["Content-Type"], "text/plain")

        # --------------------------------------------------------------

        request = self.factory.get("/content-types/text/html/")
        response = test_text_html(request)

        (content, content_type) = self.get_from_cache(request)
        self.assertEqual(content, "<b>text/html</b>", content)
        self.assertEqual(content_type, "text/html", content_type)

        response = self.client.get("/content-types/text/html/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, "<b>text/html</b>")

        headers = dict(response.items())
        self.assertEqual(headers["Content-Type"], "text/html")

    def test_etag(self):
        """Ensure the response's ETag is the cache key."""
        request = self.factory.get("/content-types/text/plain/")
        response = self.client.get("/content-types/text/plain/")
        headers = dict(response.items())
        self.assertEqual(headers["ETag"], get_cache_key(request))

    def test_timeout_argument_works(self):
        """Passing a number to cache_page caches it for that many seconds.

        It expires after that.
        """
        @cache_page(5)
        def foo(request):
            return HttpResponse("foo")

        request = self.factory.get("/")
        response = foo(request)

        time.sleep(1)
        self.assertTrue(self.get_from_cache(request) is not None)

        time.sleep(6)
        self.assertTrue(self.get_from_cache(request) is None)

    def test_get_params(self):
        url = "/content-types/text/html/?foo=bar"
        request = self.factory.get(url)
        response = self.client.get(url)
        self.assertTrue(self.get_from_cache(request))


class JimmyPageCacheabilityTests(JimmyPageTestsBase):
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


class JimmyPageBackendTests(JimmyPageTestsBase):
    def test_backend_accepts_zero(self):
        from jimmypage.backends import DefaultCache

        backend = DefaultCache("127.0.0.1:11311", {"timeout": 0})
        self.assertEqual(backend.default_timeout, 0)

        backend = DefaultCache("127.0.0.1:11311", {"timeout": None})
        self.assertEqual(backend.default_timeout, 300)

        backend = DefaultCache("127.0.0.1:11311", {"timeout": "abc"})
        self.assertEqual(backend.default_timeout, 300)

        backend = DefaultCache("127.0.0.1:11311", {"timeout": 60})
        self.assertEqual(backend.default_timeout, 60)


class JimmyPageGenerationTests(JimmyPageTestsBase):
    """
    TODO
    Tests of asynchronous cache regeneration
    """
    def test_worker_launched(self):
        """
        and check that the previous cache is served while reconstructing cache
        """
        url = "/"
        response = self.client.get(url)
        headers = dict(response.items())
        key = headers["ETag"]
        modified_model = Article(title="modified", body="modified")
        modified_model.save()
        response2 = self.client.get(url)
        headers2 = dict(response2.items())
        key2 = headers["ETag"]
        self.assertEqual(key, key2)
