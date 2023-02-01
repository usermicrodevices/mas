import logging, sys

from django.core.cache import caches
from django.db import models, transaction
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import Group
from django.apps import apps
from django.dispatch import receiver
from django.db.models.signals import post_save


def create_default_role_fields(r, rmodel, fread = False, fwrite = False):
	if r.value == 'superadmin':
		fread = True
		fwrite = True
	for field in apps.get_app_config('core').get_model(rmodel.value)._meta.get_fields():
		if field.__class__.__name__ == 'ManyToOneRel':
			continue
		try:
			rfield = RoleField.objects.get(role = r, role_model = rmodel, value = field.name)
		except:
			try:
				rfield = RoleField(role = r, role_model = rmodel, value = field.name, read = fread, write = fwrite)
			except Exception as e:
				logging.error('{} :: {} : {}'.format(sys._getframe().f_code.co_name, rmodel, e))
			else:
				rfield.save()
		else:
			if field.__class__.__name__ == 'ManyToOneRel':
				rfield.delete()
			elif field.__class__.__name__ == 'ManyToOneRel':
				rfield.delete()
			elif fread or fwrite:
				if fread:
					rfield.read = fread
				if fwrite:
					rfield.write = fwrite
				rfield.save()


class BaseModelWithLogger:

	def logi(self, *args):
		msg = f'💡{self.__class__.__name__}.{sys._getframe().f_back.f_code.co_name}'
		for arg in args: msg += f'::{arg}'
		logging.info(msg)

	def logw(self, *args):
		msg = f'⚠{self.__class__.__name__}.{sys._getframe().f_back.f_code.co_name}'
		for arg in args: msg += f'::{arg}'
		logging.warning(msg)

	def loge(self, err, *args):
		msg = f'🆘{self.__class__.__name__}.{err.__traceback__.tb_frame.f_code.co_name}::{err}::LINE={err.__traceback__.tb_lineno}'
		for arg in args: msg += f'::{arg}'
		logging.error(msg)


class RoleModel(models.Model, BaseModelWithLogger):
	value = models.CharField(max_length=128, null=False, blank=False, unique=True, verbose_name=_('value'), help_text=_('name of model'))
	description = models.CharField(max_length=191, null=True, default=None)

	class Meta:
		verbose_name = f'🤵{_("Role Model")}'
		verbose_name_plural = f'🤵{_("Role Models")}'
		ordering = ('value',)

	def __str__(self):
		return '​✅{} [{}] ({})'.format(self.id, self.value, self.description)


class Role(models.Model, BaseModelWithLogger):
	value = models.CharField(max_length=32, unique=True, null=True, default=None)
	description = models.CharField(max_length=191, null=True, default=None)
	group = models.ForeignKey(Group, default=None, null=True, blank=True, on_delete=models.SET_NULL, verbose_name=_('group'))
	weight = models.IntegerField(default=0, null=False, blank=False, verbose_name=_('weight'), help_text=_('weight of role for setup priority'))

	class Meta:
		verbose_name = f'🤵{_("Role")}'
		verbose_name_plural = f'🤵{_("Roles")}'
		ordering = ('value',)

	def __str__(self):
		return '%s : %s' % (self.value if self.value else '',  self.description if self.description else '')

	def save(self, *args, **kwargs):
		super().save(*args, **kwargs)
		for m in RoleModel.objects.all():
			create_default_role_fields(self, m)

	def users(self):
		return self.user_set.all()

	def users_count(self):
		return self.user_set.count()


class RoleField(models.Model, BaseModelWithLogger):
	value = models.CharField(max_length=191, default='id', null=False, blank=False, verbose_name=_('value'), help_text=_('field of model'))
	role = models.ForeignKey(Role, default=0, null=False, blank=False, on_delete=models.CASCADE, verbose_name=_('role'))
	role_model = models.ForeignKey(RoleModel, default=0, null=False, blank=False, on_delete=models.CASCADE, verbose_name=_('model'))
	read = models.BooleanField(null=False, blank=False, default=False)
	write = models.BooleanField(null=False, blank=False, default=False)

	class Meta:
		unique_together = ('value', 'role', 'role_model')
		verbose_name = f'🤵{_("Role Field")}'
		verbose_name_plural = f'🤵{_("Role Fields")}'
		ordering = ['value']


class User(AbstractUser, BaseModelWithLogger):
	cache = caches['users']
	role = models.ForeignKey(Role, null=True, on_delete=models.SET_NULL, verbose_name=_('role'))
	contract_finished = models.DateTimeField(default=None, null=True, blank=True, verbose_name=_('contract finished date'), help_text=_('Date of contract finished'))
	avatar = models.TextField(default=None, null=True, blank=True, verbose_name=_('avatar'), help_text=_('image as BASE64'))
	extinfo = models.JSONField(default=dict, blank=True)

	class Meta:
		db_table = 'auth_user'
		verbose_name = f'🤵{_("User")}'
		verbose_name_plural = f'🤵{_("Users")}'
		permissions = (('can_view_users_by_company', _('View users by company')),)

	def sync_from_role_group(self):
		if self.role and self.role.group and self.role.group not in self.groups.all():
			self.groups.add(self.role.group)

	def save(self, *args, **kwargs):
		super().save(*args, **kwargs)
		try:
			self.cache.clear()
		except Exception as e:
			self.loge(e)

	def update(self, *args, **kwargs):
		self.logi(args, kwargs)
		super().update(*args, **kwargs)
		try:
			self.cache.clear()
		except Exception as e:
			self.loge(e)

	def delete(self, *args, **kwargs):
		super().delete(*args, **kwargs)
		try:
			self.cache.clear()
		except Exception as e:
			self.loge(e)

@receiver(post_save, sender=User)
def user_post_save(sender, instance, created, raw, using, update_fields, **kwargs):
	if instance.role and instance.role.group and instance.role.group not in instance.groups.all():
		with transaction.atomic():
			transaction.on_commit(instance.sync_from_role_group)
