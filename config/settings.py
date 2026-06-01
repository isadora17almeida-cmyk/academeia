from pathlib import Path
import os
from dotenv import load_dotenv

try:
    import dj_database_url
except Exception:  # dj_database_url é opcional em uso local
    dj_database_url = None

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

RENDER_EXTERNAL_HOSTNAME = os.getenv('RENDER_EXTERNAL_HOSTNAME', '').strip()
SECRET_KEY = os.getenv('SECRET_KEY', 'dev-insecure-academeia-key')
DEBUG = os.getenv('DJANGO_DEBUG', os.getenv('DEBUG', 'False' if RENDER_EXTERNAL_HOSTNAME else 'True')).lower() in ('1', 'true', 'yes', 'on')

_default_hosts = '127.0.0.1,localhost,0.0.0.0,*' if DEBUG else '127.0.0.1,localhost'
ALLOWED_HOSTS = [host.strip() for host in os.getenv('ALLOWED_HOSTS', _default_hosts).split(',') if host.strip()]
if RENDER_EXTERNAL_HOSTNAME and RENDER_EXTERNAL_HOSTNAME not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

_csrf_origins = [origin.strip() for origin in os.getenv('CSRF_TRUSTED_ORIGINS', '').split(',') if origin.strip()]
if RENDER_EXTERNAL_HOSTNAME:
    _csrf_origins.append(f'https://{RENDER_EXTERNAL_HOSTNAME}')
CSRF_TRUSTED_ORIGINS = _csrf_origins

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'accounts',
    'core',
    'studies',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

DATABASE_URL = os.getenv('DATABASE_URL', '').strip()
if DATABASE_URL and dj_database_url:
    DATABASES = {
        'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600, ssl_require=DATABASE_URL.startswith('postgres'))
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'studies:dashboard'
LOGOUT_REDIRECT_URL = 'core:home'

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

MAX_UPLOAD_MB = int(os.getenv('MAX_UPLOAD_MB', '500'))
DATA_UPLOAD_MAX_MEMORY_SIZE = MAX_UPLOAD_MB * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = min(MAX_UPLOAD_MB, 25) * 1024 * 1024

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
AI_PROVIDER = os.getenv('AI_PROVIDER', 'openai').strip().lower()
GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')
GROQ_MODEL = os.getenv('GROQ_MODEL', 'llama-3.1-8b-instant')
GROQ_TRANSCRIPTION_MODEL = os.getenv('GROQ_TRANSCRIPTION_MODEL', 'whisper-large-v3')
OPENAI_TRANSCRIPTION_MODEL = os.getenv('OPENAI_TRANSCRIPTION_MODEL', 'whisper-1')

# Transcrição completa de aulas longas
# Se ffmpeg estiver instalado, o sistema divide áudio/vídeo em partes e junta o texto final.
TRANSCRIPTION_CHUNK_SECONDS = int(os.getenv('TRANSCRIPTION_CHUNK_SECONDS', '180'))
TRANSCRIPTION_OVERLAP_SECONDS = int(os.getenv('TRANSCRIPTION_OVERLAP_SECONDS', '5'))
TRANSCRIPTION_DIRECT_MAX_MB = float(os.getenv('TRANSCRIPTION_DIRECT_MAX_MB', '10'))
TRANSCRIPTION_FORCE_CHUNK_AFTER_SECONDS = int(os.getenv('TRANSCRIPTION_FORCE_CHUNK_AFTER_SECONDS', '120'))
TRANSCRIPTION_ALWAYS_CHUNK = os.getenv('TRANSCRIPTION_ALWAYS_CHUNK', 'true').lower() in ('1', 'true', 'yes', 'on')
TRANSCRIPTION_LANGUAGE = os.getenv('TRANSCRIPTION_LANGUAGE', 'pt')
