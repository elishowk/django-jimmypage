import logging

from django.conf import settings
from django.core.cache import cache
from django.db.models.signals import post_save, pre_delete
from django.db.models import get_model
from django.utils import translation
from django.core.urlresolvers import resolve
from django.utils.encoding import iri_to_uri
from django.http import HttpResponse, Http404
from hashlib import md5
import threading


logger = logging

__all__ = ('cache_page', 'clear_cache')

WHITELIST = set(get_model(*app_model.split('.')) for app_model in getattr(settings, 'JIMMY_PAGE_EXPIRATION_WHITELIST', []))
CACHE_PREFIX = getattr(settings, 'JIMMY_PAGE_CACHE_PREFIX', 'jp')
CACHE_SECONDS = getattr(settings, 'JIMMY_PAGE_CACHE_SECONDS', 0)
DISABLED = getattr(settings, 'JIMMY_PAGE_DISABLED', False)
DEBUG_CACHE = getattr(settings, 'JIMMY_PAGE_DEBUG_CACHE', False)
GLOBAL_GENERATION = CACHE_PREFIX + "_gen"
LOCK_EXPIRES = getattr(settings, 'JIMMY_PAGE_TASK_LOCK_EXPIRES', 60 * 15)
CACHE_USER_SPECIFIC = getattr(settings, 'JIMMY_PAGE_CACHE_USER_SPECIFIC', True)
MAX_CACHEKEY_REGRESSION = getattr(settings, 'JIMMY_PAGE_CACHE_USER_SPECIFIC', 25)


def clear_cache():
    logger.debug("incrementing generation")
    try:
        cache.incr(GLOBAL_GENERATION)
    except ValueError:
        cache.set(GLOBAL_GENERATION, 1)


def expire_cache(sender, instance, **kwargs):
    if instance.__class__ not in WHITELIST:
        logger.debug("%s has been saved, clear_cache" % instance.__class__)
        clear_cache()


post_save.connect(expire_cache, dispatch_uid="post_save_expire_cache")
pre_delete.connect(expire_cache, dispatch_uid="pre_delete_expire_cache")


class cache_page(object):
    """
    Decorator to invoke caching for a view.  Can be used either this way::

        uses default cache timeout
        @cache_page
        def my_view(request, ...):
            ...

    or this way::

        uses 60 seconds as cache timeout
        @cache_page(60)
        def my_view(request, ...):
            ...

    """
    def __init__(self, arg=None):
        if callable(arg):
            # we are called with a function as argument; e.g., as a bare
            # decorator.  __call__ should be the new decorated function.
            self.call = self.decorate(arg)
            self.time = CACHE_SECONDS

        else:
            # we are called with an argument.  __call__ should return
            # a decorator for its argument.
            if arg is not None:
                self.time = arg
            else:
                self.time = CACHE_SECONDS
            self.call = self.decorate

    def __call__(self, *args, **kwargs):
        return self.call(*args, **kwargs)

    def decorate(self, f):
        self.f = f
        return self.decorated

    def decorated(self, request, *args, **kwargs):
        """
        This is where Jimmypage's logic lives, dude
        """
        if not request_is_cacheable(request):
            debug("This request is NOT cacheable.")
            response = self.f(request, *args, **kwargs)
            return response
        key = get_cache_key(request)
        cached = cache.get(key)
        if cached is not None:
            debug("Found at cache: Yes. Serving %s" % key)
            (content, content_type) = cached
            response = HttpResponse(content=content, content_type=content_type, status=200, mimetype=content_type)
            response["ETag"] = key
            return response
        previous_key = None
        previous_cache = None
        minus_generation = 1
        for previous_key in range(1, MAX_CACHEKEY_REGRESSION):
            previous_key = get_cache_key(request, previous_generation=minus_generation)
            previous_cache = cache.get(previous_key)
            if previous_cache is None:
                minus_generation += 1
                continue
            debug("Found previous cache: Yes. Serving %s" % previous_key)
            (content, content_type) = previous_cache
            response = HttpResponse(content=content, content_type=content_type, status=200, mimetype=content_type)
            response["ETag"] = previous_key

            threadargs = (self.f, request, self.time, key, cache,
                          LOCK_EXPIRES, DISABLED) + args

            t = threading.Thread(target=async_update_cache,
                                 args=threadargs,
                                 kwargs=kwargs)
            t.setDaemon(True)
            t.start()
            return response

        response = build_response(self.f, request, *args, **kwargs)
        response["ETag"] = key
        cache_response(request, response, self.time, key)
        debug("NO previous cache, creating synchronously %s" % key)
        return response


def async_update_cache(fn, request, time, key, cacheapi, lock, disabled, *args, **kwargs):
    """
    asynchronously build and cache the HttpResponse
    """
    if(cacheapi.get(key + ":locked") is None):
        cacheapi.add(key + ":locked", "locked", lock)
        response = fn(request, *args, **kwargs)
        if (not disabled) and \
                response.status_code == 200 and \
                response.get('Pragma', None) != "no-cache" and \
                response.get('Vary', None) != "Cookie" and \
                not request.META.get("CSRF_COOKIE_USED", None):
            content = response.content
            content_type = dict(response.items()).get("Content-Type")
            if time is not None:
                cacheapi.set(key, (content, content_type), time)
            else:
                cacheapi.set(key, (content, content_type))
        cacheapi.delete(key + ":locked")
        return key
    return False


def cache_response(request, response, time, key):
    """
    cache the response and deletes the previous generation
    """
    if response_is_cacheable(request, response):
        content = response.content
        content_type = dict(response.items()).get("Content-Type")
        if time is not None:
            cache.set(key, (content, content_type), time)
        else:
            cache.set(key, (content, content_type))
    return


def build_response(f, request, *args, **kwargs):
    """
    immediately build the response
    """
    response = f(request, *args, **kwargs)
    return response


def get_cache_key(request, previous_generation=0):
    """
    Builds the cache key including the GENERATION number
    """
    user_id = ""
    if CACHE_USER_SPECIFIC:
        try:
            if request.user.is_authenticated():
                user_id = str(request.user.id)
        except AttributeError:  # e.g. if auth is not installed
            pass

    if previous_generation > 0:
        generation = str(cache.get(GLOBAL_GENERATION) - previous_generation)
    else:
        generation = str(cache.get(GLOBAL_GENERATION))

    try:
        host = unicode(request.get_host())
    except:
        host = "*"

    bits = {
        "cache_prefix": str(CACHE_PREFIX),
        "generation": generation,
        "path": iri_to_uri(request.path),
        "domain": host,
        "language": translation.get_language(),
        "user_id": str(user_id),
    }

    key = ":".join([
        bits["cache_prefix"],
        bits["generation"],
        bits["path"],
        bits["domain"],
        bits["language"],
        bits["user_id"]])

    digest = md5(key).hexdigest()
    return digest


def request_is_cacheable(request):
    """
    Check if request is cacheable
    """
    try:
        resolve(request.path)
    except Http404:
        debug('raised 404')
        return False
    return (not DISABLED) and request.method == "GET"


def response_is_cacheable(request, response):
    """
    Check if response is cacheable
    """
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
