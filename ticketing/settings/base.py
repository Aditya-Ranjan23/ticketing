"""
Django base settings for Ticketing project.
Designed for high traffic (e.g. ~90k concurrent users) with caching and async logging.
"""
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'change-me-in-production')

DEBUG = os.environ.get('DEBUG', 'True').lower() in ('true', '1', 'yes')

_raw_hosts = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1,[::1]').strip()
ALLOWED_HOSTS = [h.strip() for h in _raw_hosts.split(',') if h.strip()] or ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Local apps
    'events',
    'tickets',
    'orders',
    'analytics',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # User activity logging - tracks every page/action for analytics
    'analytics.middleware.UserActivityMiddleware',
]

ROOT_URLCONF = 'ticketing.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'ticketing.wsgi.application'

# Database - use PostgreSQL in production for 90k traffic
_db_engine = (os.environ.get('DB_ENGINE') or '').strip() or 'django.db.backends.sqlite3'
if not _db_engine or 'dummy' in _db_engine.lower():
    _db_engine = 'django.db.backends.sqlite3'
DATABASES = {
    'default': {
        'ENGINE': _db_engine,
        'NAME': os.environ.get('DB_NAME', str(BASE_DIR / 'db.sqlite3')).strip() or str(BASE_DIR / 'db.sqlite3'),
        'USER': os.environ.get('DB_USER', ''),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', ''),
        'PORT': os.environ.get('DB_PORT', ''),
        'CONN_MAX_AGE': 60,  # Connection pooling for production
        'OPTIONS': {} if DEBUG or _db_engine == 'django.db.backends.sqlite3' else {
            'connect_timeout': 10,
            'options': '-c statement_timeout=30000',  # 30s query timeout
        },
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ----- High-traffic: Redis cache (set REDIS_URL in production) -----
REDIS_URL = os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/0')

# Use Redis if available (install django-redis for connection pooling), else in-memory
try:
    import django_redis
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': REDIS_URL,
            'OPTIONS': {'CLIENT_CLASS': 'django_redis.client.DefaultClient'},
            'KEY_PREFIX': 'ticketing',
            'TIMEOUT': 300,
        }
    }
except ImportError:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'ticketing-default',
            'TIMEOUT': 300,
        }
    }

# Session in Redis for scale (optional; set SESSION_ENGINE in production)
# SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
# SESSION_CACHE_ALIAS = 'default'

# ----- Celery (async tasks: emails, batch activity log writes) -----
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', REDIS_URL)
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', REDIS_URL)
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TASK_ALWAYS_EAGER = os.environ.get('CELERY_ALWAYS_EAGER', 'True').lower() == 'true'  # dev: run in process

# ----- User activity logging -----
# Log to DB synchronously for small traffic; for 90k use async (Celery) or Redis stream
ANALYTICS_LOG_ASYNC = os.environ.get('ANALYTICS_LOG_ASYNC', 'False').lower() == 'true'
ANALYTICS_RATE_LIMIT_SECONDS = 2  # Min seconds between logs per session (reduce write load)

LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'
