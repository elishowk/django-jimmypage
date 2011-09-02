from django.conf.urls.defaults import patterns, include, url

urlpatterns = patterns(
    'jimmypage.test_views',
    url(r'^$', 'index'),
    url(r'^test_messages/$', 'test_messages'),
)
