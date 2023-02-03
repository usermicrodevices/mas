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


class NotificationSourceGroup(models.Model):
	name = models.CharField(max_length=191, unique=True, default='New notification group', null=False, blank=False, verbose_name=_('name'), help_text=_('Name notification group'))
	description = models.TextField(default=None, null=True, blank=True, verbose_name=_('description'), help_text=_('description of notification group'))

	class Meta:
		verbose_name = f'🔔{_("Notification Source Group")}'
		verbose_name_plural = f'🔔{_("Notification Source Groups")}'

	def __str__(self):
		return f'({self.id}) {self.name}'


class NotificationSource(models.Model):
	cache = caches['notifications']
	value = models.CharField(max_length=64, null=False, blank=False, unique=True, verbose_name=_('Value'), help_text=_('internal name notification source'))
	name = models.CharField(max_length=191, null=False, blank=False, verbose_name=_('name'), help_text=_('name notification source'))
	description = models.TextField(default=None, null=True, blank=True, verbose_name=_('Description'), help_text=_('description of notification source'))
	group = models.ForeignKey(NotificationSourceGroup, default=None, null=True, blank=True, on_delete=models.SET_NULL, verbose_name = _('group'), help_text=_('group of notifications'))

	class Meta:
		verbose_name = f'🔔{_("Notification Source")}'
		verbose_name_plural = f'🔔{_("Notification Sources")}'

	def __str__(self):
		try:
			return f'({self.id}) {self.value} :: {self.name}'
		except:
			return f'({self.id}) {self.value}'

	def save(self, *args, **kwargs):
		super().save(*args, **kwargs)
		try:
			self.cache.set('sources', NotificationSource.objects.values_list('value', flat=True), 3600)
		except:
			logging.error('{}.{}: {}'.format(self.__class__.__name__, sys._getframe().f_code.co_name, sys.exc_info()[0]))


class NotificationType(models.Model):
	value = models.CharField(max_length=64, null=False, blank=False, unique=True, verbose_name=_('Value'), help_text=_('internal name notification type'))
	name = models.CharField(max_length=191, null=False, blank=False, verbose_name=_('name'), help_text=_('name notification type'))

	class Meta:
		verbose_name = f'🔔{_("Notification Type")}'
		verbose_name_plural = f'🔔{_("Notification Types")}'

	def __str__(self):
		return f'({self.id}) {self.value}'


class NotificationTemplate(models.Model):
	source = models.ForeignKey(NotificationSource, default=0, null=False, blank=False, on_delete=models.CASCADE, verbose_name = _('source'), help_text=_('source of notification'))
	notification_type = models.ForeignKey(NotificationType, default=0, null=False, blank=False, on_delete=models.CASCADE, verbose_name = _('type'), help_text=_('type of notification'))
	body = models.TextField(default=None, null=True, blank=True, verbose_name=_('Body'), help_text=_('Body of template'))

	class Meta:
		unique_together = ('source', 'notification_type')
		verbose_name = f'🔔{_("Notification Template")}'
		verbose_name_plural = f'🔔{_("Notification Templates")}'

	def __str__(self):
		return f'({self.id}) tmpl=[{self.source.name}]'


class NotificationOption(models.Model):
	source = models.ForeignKey(NotificationSource, default=0, null=False, blank=False, on_delete=models.CASCADE, verbose_name = _('source'), help_text=_('source of notification'))
	owner = models.ForeignKey(User, default=0,  null=False, blank=False, on_delete=models.CASCADE, verbose_name=_('owner'), help_text=_('owner of notification option'))
	types = models.ManyToManyField(NotificationType, default=None, blank=True, verbose_name=_('types'), help_text=_('types of notifications'))

	class Meta:
		unique_together = ['source', 'owner']
		verbose_name = f'🔔{_("Notification Option")}'
		verbose_name_plural = f'🔔{_("Notification Options")}'
		ordering = ['source__value']

	def __str__(self):
		return f'({self.id}) opt=[{self.source.name}]'


class NotificationDelay(models.Model):
	source = models.ForeignKey(NotificationSource, default=0, null=False, blank=False, on_delete=models.CASCADE, verbose_name = _('source'), help_text=_('source of notification'))
	owner = models.ForeignKey(User, default=0,  null=False, blank=False, on_delete=models.CASCADE, verbose_name=_('owner'), help_text=_('owner of notification option'))
	interval = models.IntegerField(default=0, verbose_name = _('time interval (seconds)'), help_text=_('Time interval (seconds) between get reaction and start send notification to user'))

	class Meta:
		unique_together = ('source', 'owner')
		verbose_name = f'🔔{_("Notification Delay")}'
		verbose_name_plural = f'🔔{_("Notification Delays")}'
		ordering = ('source__value',)

	def __str__(self):
		return f'({self.id}) opt=[{self.source.name}]'


class NotificationTask(models.Model):
	created = models.DateTimeField(_('date created'), auto_now_add=True, editable=False, db_index=True)
	send_after = models.DateTimeField(_('plan time sended'), default=None, null=True, blank=True, db_index=True)
	sended = models.DateTimeField(_('date sended'), default=None, null=True, blank=True, db_index=True)
	source = models.ForeignKey(NotificationSource, default=0, null=False, blank=False, on_delete=models.CASCADE, verbose_name = _('source'), help_text=_('source of notification'))
	notification_type = models.ForeignKey(NotificationType, default=0, null=False, blank=False, on_delete=models.CASCADE, verbose_name = _('type'), help_text=_('type of notification'))
	target_user = models.ForeignKey(User, default=None,  null=True, blank=True, on_delete=models.CASCADE, verbose_name=_('target user'), help_text=_('task target user'))
	response = models.CharField(max_length=199, default=None, null=True, blank=True, verbose_name = _('response'), help_text=_('response of receiver if exists'))
	subject = models.CharField(max_length=199, default=None, null=True, blank=True, verbose_name = _('subject'), help_text=_('subject of notification'))
	content = models.TextField(default='', null=False, blank=False, verbose_name=_('target text'), help_text=_('task target text'))
	entity = models.JSONField(default=dict, blank=True, verbose_name = _('entity'), help_text=_('entity of task notification'))
	description = models.TextField(default='', null=False, blank=False, verbose_name=_('description'), help_text=_('task description'))
	reason = models.TextField(default=None, null=True, blank=True, verbose_name=_('reason'), help_text=_('task reason problems'))

	class Meta:
		unique_together = ['created_at', 'target_user', 'source', 'notification_type']
		verbose_name = '🔔{}'.format(_('Notification Task'))
		verbose_name_plural = '🔔{}'.format(_('Notification Tasks'))
		ordering = ['-id']


class NotificationBulkEmail(models.Model):
	name = models.CharField(max_length=191, unique=True, null=False, blank=False, verbose_name=_('name'), help_text=_('name bulk email list'))
	emails = models.TextField(verbose_name=_('emails'), help_text=_('list of bulk emails'))
	notifications = models.JSONField(default=list, null=False, blank=False, verbose_name=_('notification options'), help_text=_('notification options'))

	class Meta:
		verbose_name = f'📨{_("Notification Bulk Email")}'
		verbose_name_plural = f'📨{_("Notification Bulk Emails")}'
		ordering = ['name']

	def __str__(self):
		return f'({self.id}) {self.name}'
