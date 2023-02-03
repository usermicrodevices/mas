import logging, sys
from datetime import datetime as dt, timedelta

from django.db import models, transaction
from django.db.models import F, Max, Subquery, Value, IntegerField
from django.db.models.signals import pre_save, post_save, post_init
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import gettext as _
from django.core.cache import caches
from django.db.utils import IntegrityError

from users.models import User
from django.conf import settings

try:
	from zoneinfo import available_timezones, ZoneInfo
except:
	from backports.zoneinfo import available_timezones, ZoneInfo


class CustomAbstractModel(models.Model):

	class Meta:
		abstract = True

	def logi(self, *args):
		msg = f'{self.__class__.__name__}.{sys._getframe().f_back.f_code.co_name}'
		for arg in args:
			msg += f'::{arg}'
		logging.info(msg)

	def logw(self, *args):
		msg = f'{self.__class__.__name__}.{sys._getframe().f_back.f_code.co_name}'
		for arg in args:
			msg += f'::{arg}'
		logging.warning(msg)

	def loge(self, err, *args):
		msg = f'{self.__class__.__name__}.{err.__traceback__.tb_frame.f_code.co_name}::{err}::LINE={err.__traceback__.tb_lineno}'
		for arg in args:
			msg += f'::{arg}'
		logging.error(msg)


class Owner(CustomAbstractModel):
	name = models.CharField(max_length=191, null=False, blank=False, default='', verbose_name=_('name'), help_text=_('Name of owner'))
	family = models.CharField(max_length=191, null=False, blank=False, default='', verbose_name=_('family'), help_text=_('Family of owner'))
	patronymic = models.CharField(max_length=191, null=False, blank=False, default='', verbose_name=_('patronymic'), help_text=_('Patronymic of owner'))
	domain = models.CharField(max_length=191, null=False, blank=False, default='', verbose_name=_('domain'))
	login = models.CharField(max_length=191, null=False, blank=False, default='', verbose_name=_('login'), help_text=_('External login of owner for device OS or domain'))
	password = models.CharField(max_length=191, null=False, blank=False, default='', verbose_name=_('password'), help_text=_('Password of owner for external login'))
	active = models.BooleanField(default=True, null=False, verbose_name=_('active'), help_text=_('Active owner or historical record'))

	class Meta:
		verbose_name = f'🧟{_("Owner")}'
		verbose_name_plural = f'🧟{_("Owners")}'
		ordering = ['name']

	def __str__(self):
		return self.name


class Tag(CustomAbstractModel):
	name = models.CharField(max_length=191, unique=True, null=False, blank=False, default='', verbose_name=_('name'), help_text=_('Caption of tag'))
	weight = models.IntegerField(default=0, null=False, blank=False, verbose_name=_('weight'))

	class Meta:
		verbose_name = f'🍢{_("Tag")}'
		verbose_name_plural = f'🍢{_("Tags")}'
		ordering = ['name']

	def __str__(self):
		return self.name


class DeviceType(CustomAbstractModel):
	name = models.CharField(max_length=191, default='', unique=True, verbose_name=_('name'), help_text=_('Caption of type'))
	description = models.TextField(default=None, null=True, blank=True, verbose_name=_('description'), help_text=_('Description of type'))

	class Meta:
		verbose_name = f'🖥{_("Device Type")}'
		verbose_name_plural = f'🖥{_("Device Types")}'
		ordering = ['name']

	def __str__(self):
		return self.name


class DeviceGroup(CustomAbstractModel):
	parent = models.ForeignKey('self', default=None, null=True, blank=True, on_delete=models.CASCADE)
	name = models.CharField(max_length=191, null=False, blank=False, default='', verbose_name=_('name'), help_text=_('Caption of device group'))

	class Meta:
		unique_together = ('parent', 'name')
		verbose_name = f'📺{_("Device Group")}'
		verbose_name_plural = f'📺{_("Device Groups")}'
		ordering = ['name']

	def __str__(self):
		return self.name


class Device(CustomAbstractModel):
	group = models.ForeignKey(DeviceGroup, default=None, null=True, blank=True, on_delete=models.SET_NULL, verbose_name=_('group'))
	device_type = models.ForeignKey(DeviceType, default=None, null=True, blank=True, on_delete=models.SET_NULL, verbose_name=_('type'))
	created = models.DateTimeField(auto_now_add=True, verbose_name=_('created date'), help_text=_('Date of creation on server'))
	tz = models.CharField(max_length=191, choices=[(t, t) for t in sorted(available_timezones())], default=settings.TIME_ZONE, null=False, blank=False, verbose_name=_('timezone'), help_text=_('Timezone of dates'))
	status = models.IntegerField(default=0, verbose_name=_('status'), help_text=_('Status of device (on=1, off=0, not used=-1)'))
	tags = models.ManyToManyField(Tag, blank=True, verbose_name=_('tags'))
	extinfo = models.JSONField(default=dict, blank=True)

	class Meta:
		verbose_name = f'💻{_("Device")}'
		verbose_name_plural = f'💻{_("Devices")}'
		ordering = ['name']

	def __str__(self):
		return self.name

	def get_absolute_url(self):
		try:
			return f'https://{settings.HOST}/devices/{self.id}/'
		except:
			return f'https://{settings.HOST}/devices/'

	def now_tz(self):
		try:
			return timezone.now().astimezone(ZoneInfo(self.tz))
		except:
			return timezone.now().astimezone(ZoneInfo(settings.TIME_ZONE))

	def date_tz(self, value, tz=None):
		if timezone.is_naive(value):
			value = value.replace(tzinfo=ZoneInfo(tz) if tz else timezone.utc)
		return value

	def dtz_from_timestamp(self, value):
		return self.date_tz(dt.utcfromtimestamp(value))


class History(CustomAbstractModel):
	created = models.DateTimeField(_('created date'), auto_now_add=True, help_text=_('Date of creation new record'))
	closed = models.DateTimeField(_('closed date'), default=None, null=True, blank=True, db_index=True, help_text=_('Closed date of history'))
	device = models.ForeignKey(Device, default=0, null=False, blank=False, on_delete=models.CASCADE, verbose_name=_('device'))
	owner = device = models.ForeignKey(Owner, default=0, null=False, blank=False, on_delete=models.CASCADE, verbose_name=_('device'))

	class Meta:
		unique_together = ['created', 'device', 'owner']
		verbose_name = f'📜{_("History")}'
		verbose_name_plural = f'📜{_("Histories")}'
		ordering = ['name']
