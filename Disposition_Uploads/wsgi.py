"""
WSGI config for Disposition_Uploads project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Disposition_Uploads.settings')

application = get_wsgi_application()
from whitenoise import WhiteNoise
application = WhiteNoise(application, root=os.path.join(BASE_DIR, 'staticfiles'))
