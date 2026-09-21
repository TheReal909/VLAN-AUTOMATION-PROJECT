from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BASE_DIR.parent

env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(ROOT_DIR / ".env")

SECRET_KEY = env("SECRET_KEY", default="development-secret-key")
DEBUG = env("DEBUG", default=True)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1", "0.0.0.0"])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "inventory",
    "discovery",
    "changes",
    "audit",
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
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": env.db(default="postgresql://postgres:postgres@localhost:5432/vlan_portal")
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="redis://localhost:6379/0")

DISCOVERY_SSH_USERNAME = env("DISCOVERY_SSH_USERNAME", default="")
DISCOVERY_SSH_PASSWORD = env("DISCOVERY_SSH_PASSWORD", default="")
DISCOVERY_SSH_PORT = env.int("DISCOVERY_SSH_PORT", default=22)
DISCOVERY_SSH_TIMEOUT = env.int("DISCOVERY_SSH_TIMEOUT", default=10)
CHANGE_EXECUTION_ENABLED = env.bool("CHANGE_EXECUTION_ENABLED", default=False)
CHANGE_COMMAND_MODE = env("CHANGE_COMMAND_MODE", default="legacy").lower()
CHANGE_SSH_USERNAME = env("CHANGE_SSH_USERNAME", default="")
CHANGE_SSH_PASSWORD = env("CHANGE_SSH_PASSWORD", default="")
CHANGE_SSH_PORT = env.int("CHANGE_SSH_PORT", default=22)
CHANGE_SSH_TIMEOUT = env.int("CHANGE_SSH_TIMEOUT", default=10)

# Optional LDAP configuration for direct AD/LDAPS auth
LDAP_SERVER_URI = env("LDAP_SERVER_URI", default="")
LDAP_BIND_DN = env("LDAP_BIND_DN", default="")
LDAP_BIND_PASSWORD = env("LDAP_BIND_PASSWORD", default="")
LDAP_USER_DN_TEMPLATE = env("LDAP_USER_DN_TEMPLATE", default="")

if LDAP_SERVER_URI:
    import ldap

    AUTHENTICATION_BACKENDS = [
        "django_auth_ldap.backend.LDAPBackend",
        "django.contrib.auth.backends.ModelBackend",
    ]
    AUTH_LDAP_SERVER_URI = LDAP_SERVER_URI
    AUTH_LDAP_BIND_DN = LDAP_BIND_DN
    AUTH_LDAP_BIND_PASSWORD = LDAP_BIND_PASSWORD
    AUTH_LDAP_USER_DN_TEMPLATE = LDAP_USER_DN_TEMPLATE
    AUTH_LDAP_ALWAYS_UPDATE_USER = True
    AUTH_LDAP_CACHE_TIMEOUT = 3600
    AUTH_LDAP_GLOBAL_OPTIONS = {ldap.OPT_REFERRALS: 0}
else:
    AUTHENTICATION_BACKENDS = ["django.contrib.auth.backends.ModelBackend"]
