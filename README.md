# django-jimmypage

Jimmy Page is a generational caching app for Django views.

Each time a model is saved, if it's not blacklisted (see settings below), Jimmypage will
invalidate all previously cached entries, and throw a python thread to refresh asynchronously the cache,
but will return anyway the last cache entry.

While the actual cache generation number is not available, Jimmypage also tries to serve the previous
generation of cache before synchronously building the requested response.

> "There are only two hard things in Computer Science: cache invalidation and naming things." - Phil Karlton

## Based on

  * https://github.com/edavis/django-jimmypage
  * https://github.com/alanjds/django-jimmypage

## Dependencies

 * Johnny-cache provides the infinite caching backends
 * Python threads builds and caches views when they become obsolete

## What is Generational Caching?

So how do generational and "regular" caching differ?  The biggest
difference is how they handle stale content.

Regular caching is designed so that after *N* seconds, the cached
content expires.  Then, once expired, the next request comes along and
-- finding the cached content newly expired -- repopulates it with
(potentially) fresher content.

It's not hard to see the downsides to this method.  You're constantly
trying to find a balance between setting that *N* too low (which gives
you fresher content at the expense of hammering your database) and too
high (which eases off your database but increases the chance of
serving stale content).  But beyond that, what if the content hasn't
changed since it was cached?  Why keep hitting a database looking for
fresh content when there isn't anything fresher?

#### Wouldn't it just make more sense to keep serving the cached content until you have a reason not to?

That's where generational caching comes in.

The central feature in generational caching is something called a
"generation."  It's just a number -- stored in your cache -- that you
increment whenever you want to invalidate items in your cache.

The idea is to increment this generation number whenever you add,
update, or delete a record in your database.

When building your cache keys, you include this generation number in
the key. As long as the generation number stays the same, the key will
continue serve the same content.  But when you increment the
generation -- say, after adding a database record -- all cache keys
that include the generation number become transparently invalidated.

While the actual generation number is not available, Jimmypage tries to serve the previous
generation of cache and throws a Celery Task to refresh the missing cache.


Installation

This is the first, as yet largely untested alpha release.  Some notes:

* If you have any custom SQL that updates the database without emitting
  ``post_save`` or ``pre_delete`` signals, things might get screwy.  At this
  stage, Jimmy Page works best with sites using vanilla ORM calls.

Install using pip::

    pip install -e git://github.com/elishowk/django-jimmypage.git#egg=django-jimmypage

or clone the git archive and use setup.py::

    python setup.py install

# Usage

To use, include ``jimmypage`` in your INSTALLED_APPS setting, and define some constants in your settings.py file::

    # settings.py
    INSTALLED_APPS = (
        ...
        "jimmypage",
        ...
    )
    JIMMY_PAGE_CACHE_PREFIX = "jp_mysite" # to prefix your cache keys
    JIMMY_PAGE_CACHE_SECONDS = 0 # to get infinite caching periods
    JIMMY_PAGE_DISABLED = False # nothing will be cached
    JIMMY_PAGE_DEBUG_CACHE = False # to get debugging logs
    JIMMY_PAGE_TASK_LOCK_EXPIRES = 60*15 # to avoid duplicate async cache refreshing task, but limited to a certain amount of time

Any update to any table will clear the cache (by incrementing the generation),
unless the tables are included in the ``JIMMY_PAGE_EXPIRATION_WHITELIST``.  The
defaults can be overridden by defining it in your settings.py.  By default it
includes::

    JIMMY_PAGE_EXPIRATION_WHITELIST = [
        "django_session",
        "django_admin_log",
        "registration_registrationprofile",
        "auth_message",
        "auth_user",
    ]

To cache a view, use the ``cache_page`` decorator::

    from jimmypage.cache import cache_page

    @cache_page
    def myview(request):
        ...


Views are cached on a per-user, per-language, per-path, per-host  basis.  Anonymous users
share a cache, but authenticated users get a separate cache, ensuring that no
user will ever see another's user-specific content.  The cache is only used if:

* Jimmy page is not DISABLED
* The request method is ``GET``
* There are no [messages](http://docs.djangoproject.com/en/dev/ref/contrib/messages/) stored for the request
* The response status is 200
* The response does not contain a ``Pragma: no-cache`` header
* The response does not contain a ``Vary: Cookie`` header
* The request.META does not have CSRF_COOKIE_USED

> Please contribute any bugs or improvements to help make this better!

## TODO

Current TODOs include:

* Much more testing, analysis, and code review
