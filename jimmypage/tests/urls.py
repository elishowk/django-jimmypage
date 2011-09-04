from django.conf.urls.defaults import patterns, include, url

urlpatterns = patterns(
    'jimmypage.tests.views',
    url(r'^$', 'index'),
    url(r'^test_messages/$', 'test_messages'),
    url(r'^content-types/text/plain/$', 'test_text_plain'),
    url(r'^content-types/text/html/$', 'test_text_html'),
)
