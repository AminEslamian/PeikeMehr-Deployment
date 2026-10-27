"""
Django settings for Peykemehr.

Configuration is environment driven. Do not hard-code secrets here.
See docs/production-environment.example for the full list of variables.
"""

from datetime import timedelta
from pathlib import Path
import os
import sys

from django.core.exceptions import ImproperlyConfigured


BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def env_list(name: str, default: str = "") -> list[str]:
    return [
        item.strip()
        for item in os.getenv(name, default).split(",")
        if item.strip()
    ]


# ---------------------------------------------------------------------------
# Core / security
# ---------------------------------------------------------------------------

SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
DEBUG = env_bool("DJANGO_DEBUG", False)

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS", "")

# Nginx in front of Django sets this header. Keep the backend unpublished.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", False)
SECURE_REDIRECT_EXEMPT = [r"^health/$"]
SESSION_COOKIE_SECURE = env_bool("DJANGO_SESSION_COOKIE_SECURE", False)
CSRF_COOKIE_SECURE = env_bool("DJANGO_CSRF_COOKIE_SECURE", False)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

# Enable only after HTTPS is verified for the real domain.
SECURE_HSTS_SECONDS = env_int("DJANGO_SECURE_HSTS_SECONDS", 0)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool(
    "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", False
)
SECURE_HSTS_PRELOAD = env_bool("DJANGO_SECURE_HSTS_PRELOAD", False)

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"


# ---------------------------------------------------------------------------
# SMS / OTP
# ---------------------------------------------------------------------------

SMS_PROVIDER = os.getenv("SMS_PROVIDER", "disabled").strip().lower()
SMS_IR_API_KEY = os.getenv("SMS_IR_API_KEY", "")
SMS_IR_TEMPLATE_ID = env_int("SMS_IR_TEMPLATE_ID", 0)
SMS_IR_VERIFY_URL = os.getenv(
    "SMS_IR_VERIFY_URL", "https://api.sms.ir/v1/send/verify"
)
SMS_ALLOW_MOCK = env_bool("SMS_ALLOW_MOCK", False)
SMS_REQUEST_TIMEOUT = env_int("SMS_REQUEST_TIMEOUT", 10)
SMS_MAX_RETRIES = env_int("SMS_MAX_RETRIES", 2)

OTP_EXPIRE_MINUTES = env_int("OTP_EXPIRE_MINUTES", 3)
OTP_MAX_ATTEMPTS = env_int("OTP_MAX_ATTEMPTS", 5)
OTP_RESEND_SECONDS = env_int("OTP_RESEND_SECONDS", 60)

# Local Docker/testing only. Codes are only logged by the mock SMS provider;
# production uses the real "sms_ir" provider, so this flag has no effect there.
OTP_LOG_CODES = env_bool("OTP_LOG_CODES", False)


# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    "django_filters",
    "rest_framework",
    "accounts",
    "reports",
    "nested_admin",
    "survey",
    "adminpanel",
    "blogs",
    "tickets",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

if os.getenv("POSTGRES_DB"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ["POSTGRES_DB"],
            "USER": os.getenv("POSTGRES_USER", "peykemehr"),
            "PASSWORD": os.getenv("POSTGRES_PASSWORD", ""),
            "HOST": os.getenv("POSTGRES_HOST", "db"),
            "PORT": os.getenv("POSTGRES_PORT", "5432"),
            "CONN_MAX_AGE": env_int("DB_CONN_MAX_AGE", 60),
            "CONN_HEALTH_CHECKS": True,
            "OPTIONS": {
                "connect_timeout": env_int("DB_CONNECT_TIMEOUT", 5),
            },
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": os.getenv(
                "SQLITE_PATH", str(BASE_DIR / "db.sqlite3")
            ),
            "OPTIONS": {"timeout": env_int("SQLITE_TIMEOUT", 20)},
        }
    }


# ---------------------------------------------------------------------------
# Cache (used by DRF throttling)
# ---------------------------------------------------------------------------

# File based so that the Gunicorn workers share the throttle counters.
# For multiple hosts / containers use Redis and set CACHE_BACKEND accordingly.
CACHES = {
    "default": {
        "BACKEND": os.getenv(
            "CACHE_BACKEND",
            "django.core.cache.backends.filebased.FileBasedCache",
        ),
        "LOCATION": os.getenv("CACHE_LOCATION", "/tmp/peykemehr-cache"),
    }
}

# Keep throttling state isolated and in-process during the test run.
if "test" in sys.argv:
    CACHES["default"] = {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "peykemehr-tests",
    }


# ---------------------------------------------------------------------------
# Authentication / API
# ---------------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

AUTH_USER_MODEL = "accounts.Teacher"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_RATES": {
        "otp_send": os.getenv("OTP_SEND_RATE", "30/min"),
        "otp_verify": os.getenv("OTP_VERIFY_RATE", "60/min"),
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=env_int("JWT_ACCESS_MINUTES", 60)
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=env_int("JWT_REFRESH_DAYS", 7)
    ),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": False,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

API_DOCS_PUBLIC = env_bool("API_DOCS_PUBLIC", DEBUG)

SPECTACULAR_SETTINGS = {
    "TITLE": "Safiremehr API",
    "DESCRIPTION": (
        "مستندات تعاملی API. برای تست اندپوینت‌های محافظت‌شده، "
        "از Authorize استفاده کنید و Access Token را به‌صورت "
        "`Bearer <access>` وارد کنید."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SERVE_PERMISSIONS": (
        ["rest_framework.permissions.AllowAny"]
        if API_DOCS_PUBLIC
        else ["rest_framework.permissions.IsAdminUser"]
    ),
    "SERVE_AUTHENTICATION": None,
    "COMPONENT_SPLIT_REQUEST": True,
    "TAGS": [
        {"name": "Auth", "description": "ورود و ثبت‌نام با OTP"},
        {"name": "Reports", "description": "گزارش‌ها، تگ‌ها و امتیاز معلم"},
        {"name": "Surveys", "description": "نظرسنجی و ثبت پاسخ"},
        {"name": "Blogs", "description": "بلاگ (خواندن برای معلم، نوشتن برای ادمین)"},
        {"name": "Tickets", "description": "تیکت‌های معلم"},
        {"name": "Admin Teachers", "description": "مدیریت معلمان"},
        {"name": "Admin Tags", "description": "مدیریت تگ‌ها"},
        {"name": "Admin Reports", "description": "مدیریت گزارش‌ها"},
        {"name": "Admin Media", "description": "تصاویر، ویدیوها و لیست رسانه"},
        {"name": "Admin Points", "description": "امتیاز معلمان"},
        {"name": "Admin Surveys", "description": "نظرسنجی، سوال، گزینه، پاسخ"},
        {"name": "Admin Tickets", "description": "پاسخ به تیکت‌ها"},
    ],
    "SWAGGER_UI_SETTINGS": {
        "persistAuthorization": True,
        "displayRequestDuration": True,
        "filter": True,
        "tryItOutEnabled": True,
        "deepLinking": True,
    },
    "PREPROCESSING_HOOKS": [
        "drf_spectacular.hooks.preprocess_exclude_path_format",
    ],
}


# ---------------------------------------------------------------------------
# Static and media files
# ---------------------------------------------------------------------------

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = os.getenv("STATIC_ROOT", str(BASE_DIR / "staticfiles"))
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

MEDIA_URL = os.getenv("MEDIA_URL", "/media/")
MEDIA_ROOT = os.getenv("MEDIA_ROOT", str(BASE_DIR / "media"))

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ---------------------------------------------------------------------------
# Upload limits
# ---------------------------------------------------------------------------

MAX_UPLOAD_SIZE_MB = env_int("MAX_UPLOAD_SIZE_MB", 300)
MAX_UPLOAD_SIZE = MAX_UPLOAD_SIZE_MB * 1024 * 1024
MAX_UPLOAD_FILES = env_int("MAX_UPLOAD_FILES", 10)
DATA_UPLOAD_MAX_MEMORY_SIZE = env_int(
    "DATA_UPLOAD_MAX_MEMORY_SIZE", 10 * 1024 * 1024
)
FILE_UPLOAD_MAX_MEMORY_SIZE = env_int(
    "FILE_UPLOAD_MAX_MEMORY_SIZE", 10 * 1024 * 1024
)
DATA_UPLOAD_MAX_NUMBER_FIELDS = env_int(
    "DATA_UPLOAD_MAX_NUMBER_FIELDS", 1000
)


# ---------------------------------------------------------------------------
# Object storage (S3 compatible)
# ---------------------------------------------------------------------------

STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "local").strip().lower()
S3_ENABLED = STORAGE_BACKEND in {"s3", "minio", "r2", "s3-compatible"}

if S3_ENABLED:
    _s3_endpoint = os.getenv("AWS_S3_ENDPOINT_URL", "").strip()
    if _s3_endpoint and not _s3_endpoint.startswith(("http://", "https://")):
        _s3_endpoint = f"https://{_s3_endpoint}"

    _s3_required = {
        "AWS_ACCESS_KEY_ID": os.getenv("AWS_ACCESS_KEY_ID", "").strip(),
        "AWS_SECRET_ACCESS_KEY": os.getenv(
            "AWS_SECRET_ACCESS_KEY", ""
        ).strip(),
        "AWS_STORAGE_BUCKET_NAME": os.getenv(
            "AWS_STORAGE_BUCKET_NAME", ""
        ).strip(),
        "AWS_S3_ENDPOINT_URL": _s3_endpoint,
        "AWS_S3_REGION_NAME": os.getenv(
            "AWS_S3_REGION_NAME", ""
        ).strip(),
    }
    _missing_s3_settings = [
        name for name, value in _s3_required.items() if not value
    ]
    if _missing_s3_settings:
        raise ImproperlyConfigured(
            "Object storage is enabled but these settings are missing: "
            + ", ".join(_missing_s3_settings)
        )

    _s3_options = {
        "access_key": _s3_required["AWS_ACCESS_KEY_ID"],
        "secret_key": _s3_required["AWS_SECRET_ACCESS_KEY"],
        "security_token": os.getenv("AWS_SESSION_TOKEN") or None,
        "bucket_name": _s3_required["AWS_STORAGE_BUCKET_NAME"],
        "endpoint_url": _s3_endpoint,
        "region_name": _s3_required["AWS_S3_REGION_NAME"],
        "custom_domain": os.getenv("AWS_S3_CUSTOM_DOMAIN") or None,
        "addressing_style": os.getenv("AWS_S3_ADDRESSING_STYLE", "path"),
        "signature_version": os.getenv("AWS_S3_SIGNATURE_VERSION", "s3v4"),
        "querystring_auth": env_bool("AWS_QUERYSTRING_AUTH", True),
        "querystring_expire": env_int("AWS_QUERYSTRING_EXPIRE", 3600),
        "file_overwrite": env_bool("AWS_S3_FILE_OVERWRITE", False),
        # Leave object ACLs unset so the bucket's private default applies.
        "default_acl": None,
        "object_parameters": {
            "CacheControl": os.getenv(
                "AWS_S3_CACHE_CONTROL", "private, max-age=3600"
            ),
        },
    }
    _s3_options = {
        key: value for key, value in _s3_options.items() if value is not None
    }

    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3.S3Storage",
            "OPTIONS": _s3_options,
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
else:
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }

# Tests must never write to, or delete from, the real object-storage bucket.
# Integration against the real bucket is performed explicitly with the
# check_storage management command instead.
if "test" in sys.argv:
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }


# ---------------------------------------------------------------------------
# Logging (never log OTP codes unless OTP_LOG_CODES is explicitly enabled,
# never log SMS keys or request bodies)
# ---------------------------------------------------------------------------

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "{levelname} {asctime} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": os.getenv("DJANGO_LOG_LEVEL", "INFO"),
    },
    "loggers": {
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "django.security": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "accounts": {
            "handlers": ["console"],
            "level": os.getenv("APP_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
        "reports": {
            "handlers": ["console"],
            "level": os.getenv("APP_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
    },
}
