DATABASES = {
    "default": {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
    },
}

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    "jimmypage",
    "testapp",
]

CACHES = {
    "default": {
        "BACKEND": "jimmypage.backends.DefaultCache",
        "KEY_PREFIX": "jimmypage.tests.settings",
    },
}

ROOT_URLCONF = 'jimmypage.tests.urls'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'console': {
            'format': '%(name)s %(levelname)s %(message)s',
        },
    },

    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler'
        },

        'console': {
            'class': 'logging.StreamHandler',
            'level': 'DEBUG',
            'formatter': 'console',
        },
    },

    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
        'jimmypage': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    }
}
