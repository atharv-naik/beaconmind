# settings/prod.py

import os
from .base import *

# Production-specific settings
DEBUG = False
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')

# Additional security settings for production
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
CSRF_TRUSTED_ORIGINS = os.getenv('CSRF_TRUSTED_ORIGINS', '').split(',')

# Ensure the production environment variables (like SECRET_KEY, ALLOWED_HOSTS, etc.)
# are correctly set in your .env.prod file.
