import logging, socket, json, sys
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _
from django.conf import settings


class CoreConfig(AppConfig):
	name = 'notifications'
	verbose_name = _('Notifications')
