import os
from pathlib import Path
from decouple import config, Csv
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

# === SECURITY ===
# Both of these MUST come from environment variables. Never hardcode.
SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)

# Comma-separated list in .env, e.g: ALLOWED_HOSTS=127.0.0.1,localhost,yourapp.up.railway.app
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='127.0.0.1,localhost', cast=Csv())

# Comma-separated list, e.g: CSRF_TRUSTED_ORIGINS=https://yourapp.up.railway.app
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='', cast=Csv())


# === APPLICATIONS ===
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sitemaps',

    'nested_admin',
    'cloudinary_storage',
    'cloudinary',

    'shop_project',  # this app - rename if your app is named differently
]
SITE_ID = 1
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # serves static files in prod
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'joy.urls'  # rename 'core' to your actual project folder name

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'shop_project' / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'joy.wsgi.application'  # rename 'core' to your actual project folder name


# === DATABASE ===
# Reads DATABASE_URL from env (Railway provides this automatically for Postgres)
DATABASES = {
    'default': dj_database_url.config(
        default=config('DATABASE_URL', default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}"),
        conn_max_age=600,
    )
}


# === PASSWORD VALIDATION ===
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# === INTERNATIONALIZATION ===
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Lagos'
USE_I18N = True
USE_TZ = True


# === STATIC & MEDIA FILES ===

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.StaticFilesStorage'
#STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
#STATICFILES_DIRS = [
    #os.path.join(BASE_DIR,'static')
#]


# Required for the static() helper in urls.py during local dev,
# even though Cloudinary handles actual file storage.
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Cloudinary handles all uploaded media (product/variant images)

CLOUDINARY_STORAGE = {
    'CLOUD_NAME': config('CLOUDINARY_CLOUD_NAME'),
    'API_KEY': config('CLOUDINARY_API_KEY'),
    'API_SECRET': config('CLOUDINARY_API_SECRET'),
}
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage' 


# === AUTH / LOGIN ===
LOGIN_URL = '/admin/login/'
LOGIN_REDIRECT_URL = '/admin/'


# === MISC ===
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
