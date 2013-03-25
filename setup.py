#!/usr/bin/env python

import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'jimmypage.tests.settings'

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

VERSION = '0.2'

setup(
    name='django-jimmypage',
    version=VERSION,
    description="Generational and asynchronous view caching for Django",
    author='Elias Showk',
    author_email='elias.showk@gmail.com ',
    url='http://github.com/elishowk/jimmypage',
    packages=['jimmypage'],
    test_suite='jimmypage.tests.runtests.runtests',
    long_description=open('README.md').read(),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU Affero General Public License v3',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
    ],
    install_requires=[
        "Django >= 1.3",
        "johnny-cache >= 1.4",
    ],
)
