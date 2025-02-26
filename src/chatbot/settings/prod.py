# settings/prod.py

from dotenv import load_dotenv
import os
from .base import *

# Load production environment variables
load_dotenv(dotenv_path='.env.prod')

# Production-specific settings
DEBUG = False
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')

# Additional security settings for production
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
CSRF_TRUSTED_ORIGINS = os.getenv('CSRF_TRUSTED_ORIGINS', '').split(',')

# Ensure the production environment variables (like SECRET_KEY, ALLOWED_HOSTS, etc.)
# are correctly set in your .prod.env file.

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs/django.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['file', 'mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['file'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

# Progressive Web App (PWA) settings
PWA_APP_NAME = "AI4MentalWellness"
PWA_APP_DESCRIPTION = "LLM powered chatbot designed for conducting assessments and monitoring"
PWA_APP_THEME_COLOR = "#FFFFFF"
PWA_APP_BACKGROUND_COLOR = "#000000"
PWA_APP_DISPLAY = "standalone"
PWA_APP_START_URL = "/"
PWA_APP_ORIENTATION = "portrait"
PWA_APP_SCOPE = "/"

