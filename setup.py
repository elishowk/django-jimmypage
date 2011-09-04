#!/usr/bin/env python

import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'jimmypage.tests.settings'

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

VERSION = '0.1'

setup(
    name='django-jimmypage',
    version=VERSION,
    description="Generational page caching for Django",
    author='Charlie DeTar',
    author_email='cfd@media.mit.edu',
    url='http://github.com/yourcelf/jimmypage',
    packages=['jimmypage'],
    test_suite='jimmypage.tests.runtests.runtests',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
    ],
)

