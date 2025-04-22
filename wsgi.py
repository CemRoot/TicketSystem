"""
WSGI config for TicketSystem project.

It exposes the WSGI callable as a module-level variable named ``application``.
"""

import os
from pathlib import Path
import sys
from django.core.wsgi import get_wsgi_application

# Add the project directory to the sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')

application = get_wsgi_application()
