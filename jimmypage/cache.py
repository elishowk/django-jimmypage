import urllib
import logging

from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.db.models.signals import post_save, pre_delete
from django.http import HttpResponse
from django.utils import translation
from django.utils.encoding import iri_to_uri
from django.utils.hashcompat import md5_constructor

logger = logging.getLogger("jimmypage")

__all__ = ('cache_page', 'clear_cache')

CACHE_PREFIX = getattr(settings, 'JIMMY_PAGE_CACHE_PREFIX', 'jp')
CACHE_SECONDS = getattr(settings, 'JIMMY_PAGE_CACHE_SECONDS', 0)
DISABLED = getattr(settings, 'JIMMY_PAGE_DISABLED', False)
EXPIRATION_WHITELIST = set(getattr(settings,
    'JIMMY_PAGE_EXPIRATION_WHITELIST',
    [
        "django_session",
        "django_admin_log",
        "registration_registrationprofile",
        "auth_message",
        "auth_user",
    ]))
DEBUG_CACHE = getattr(settings, 'JIMMY_PAGE_DEBUG_CACHE', False)
GLOBAL_GENERATION = CACHE_PREFIX + "_gen"

def clear_cache():
    debug("###### Incrementing Generation")
    try:
        cache.incr(GLOBAL_GENERATION)
    except ValueError:
        cache.set(GLOBAL_GENERATION, 1)

def expire_cache(sender, instance, **kwargs):
    table = instance._meta.db_table
    if table not in EXPIRATION_WHITELIST:
        clear_cache()
post_save.connect(expire_cache)
pre_delete.connect(expire_cache)

class cache_page(object):
    """
    Decorator to invoke cacheing for a view.  Can be used either this way::

        # uses default cache timeout
        @cache_page
        def my_view(request, ...):
            ...

    or this way::

        # uses 60 seconds as cache timeout
        @cache_page(60)
        def my_view(request, ...):
            ...

    """
    def __init__(self, arg=None):
        if callable(arg):
            # we are called with a function as argument; e.g., as a bare
            # decorator.  __call__ should be the new decorated function.
            self.time = CACHE_SECONDS
            self.call = self.decorate(arg)

        else:
            # we are called with an argument.  __call__ should return
            # a decorator for its argument.
            if arg is None:
                self.time = CACHE_SECONDS
            else:
                self.time = arg
            self.call = self.decorate

    def __call__(self, *args, **kwargs):
        return self.call(*args, **kwargs)

    def decorate(self, f):
        self.f = f
        return self.decorated

    def decorated(self, request, *args, **kwargs):
        if request_is_cacheable(request):
            key = get_cache_key(request)
            debug("This request is cacheable.")
            cached = cache.get(key)
            if cached is not None:
                debug("Found at cache: Yes. Serving cached")
                (content, content_type) = cached
                res = HttpResponse(content=content, content_type=content_type)
                res["ETag"] = key
                return res
            else:
                debug("Found at cache: NO")

            response = self.f(request, *args, **kwargs)
            if response_is_cacheable(request, response):
                debug("Storing response in cache: Yes")
                content = response.content
                content_type = dict(response.items()).get("Content-Type")
                cache.set(key, (content, content_type), self.time)
            else:
                debug("Storing response in cache: NO. Isn't cacheable")
            response["ETag"] = key
            return response
        debug("This request is NOT cacheable.")
        return self.f(request, *args, **kwargs)

def get_cache_key(request):
    user_id = ""
    try:
        if request.user.is_authenticated():
            user_id = str(request.user.id)
    except AttributeError: # e.g. if auth is not installed
        pass

    bits = {
        "cache_prefix": str(CACHE_PREFIX),
        "generation": str(cache.get(GLOBAL_GENERATION)),
        "path": iri_to_uri(request.path),
        "domain": unicode(request.site.domain) if hasattr(request, 'site') else "*",
        "get_params": urllib.urlencode(request.GET),
        "language": translation.get_language(),
        "user_id": str(user_id),
    }

    key = ":".join([
        bits["cache_prefix"],
        bits["generation"],
        bits["path"],
        bits["domain"],
        bits["get_params"],
        bits["language"],
        bits["user_id"]])

    digest = md5_constructor(key).hexdigest()
    debug("Jimmy-Page cache key: %r (%s)" % (bits, digest))
    return "%s.%s" % (bits["cache_prefix"], digest)

def request_is_cacheable(request):
    return (not DISABLED) and \
            request.method == "GET" and \
            len(messages.get_messages(request)) == 0

def response_is_cacheable(request, response):
    return (not DISABLED) and \
        response.status_code == 200 and \
        response.get('Pragma', None) != "no-cache" and \
        response.get('Vary', None) != "Cookie" and \
        not request.META.get("CSRF_COOKIE_USED", None)

if DEBUG_CACHE:
    def debug(*args):
        logger.debug(" ".join([str(a) for a in args]))
else:
    def debug(*args):
        pass

clear_cache()
