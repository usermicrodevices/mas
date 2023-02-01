import inspect, logging, sys, xlsxwriter
from io import BytesIO
from datetime import datetime, timedelta
try:
	from zoneinfo import available_timezones, ZoneInfo
except:
	from backports.zoneinfo import available_timezones, ZoneInfo

from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.html import format_html, format_html_join
from django.urls import reverse, path
from django.utils.safestring import mark_safe
from django.contrib import admin, messages
from django import forms
from django.http import StreamingHttpResponse, FileResponse, HttpResponseRedirect
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.db.models import F, Q, Min, Max, Value, Count, IntegerField, TextField, CharField, OuterRef, Subquery
from django.db.models.query import QuerySet
from django.db import connections
from django.contrib.admin.models import LogEntry
from django.contrib.admin.widgets import AutocompleteSelect
from django.shortcuts import render
from django.views.generic.edit import FormView

from django.conf import settings

from django_select2.forms import Select2Widget

from .models import CustomAbstractModel, DeviceType, Device, NotificationSource, NotificationType, NotificationTemplate, NotificationSourceGroup, NotificationOption, NotificationDelay, NotificationTask, NotificationBulkEmail

from users.models import User

list_models = inspect.getmembers(sys.modules['core.models'], inspect.isclass)
exclude_classes = [CustomAbstractModel, DeviceType, Device, User, NotificationSource, NotificationType, NotificationTemplate, NotificationSourceGroup, NotificationOption, NotificationDelay, NotificationTask, NotificationBulkEmail]

for name_class, model_class in list_models:
	mname = model_class.__module__
	if model_class not in exclude_classes and 'django.' not in mname and 'zoneinfo' not in mname and 'datetime' not in mname and 'datetime' not in model_class.__name__:
		try:
			admin.site.register(model_class)
		except Exception as e:
			logging.warning('Error registering model {} for admin UI: {}'.format(model_class, e))


class DropDownFilter(admin.SimpleListFilter):
	template = 'dropdown_filter_from_memory.html'


class DeviceTypeFilter(DropDownFilter):
	title = _('Device Type')
	parameter_name = 'device_type'

	def lookups(self, request, model_admin):
		res = []
		queryset = DeviceType.objects.only('id', 'name')
		for it in queryset:
			res.append((it.id, it.name))
		return res

	def queryset(self, request, queryset):
		if not self.value():
			return queryset
		else:
			return queryset.filter(device_type=self.value())


class NotificationSourceFilter(DropDownFilter):
	title = _('Notification Source')
	parameter_name = 'source'

	def lookups(self, request, model_admin):
		user = request.user
		res = []
		for item in NotificationSource.objects.only('id', 'name'):
			res.append((item.id, item.name))
		return res

	def queryset(self, request, queryset):
		if not self.value():
			return queryset
		else:
			return queryset.filter(source=self.value())


class UserFilter(DropDownFilter):
	title = _('User')
	parameter_name = 'user'

	def lookups(self, request, model_admin):
		user = request.user
		res = []
		for item in User.objects.order_by('username').only('id', 'username'):
			res.append((item.id, item.username))
		return res

	def queryset(self, request, queryset):
		if not self.value():
			return queryset
		else:
			return queryset.filter(user=self.value())
class OwnerFilter(UserFilter):
	parameter_name = 'owner'
	def queryset(self, request, queryset):
		if not self.value():
			return queryset
		else:
			return queryset.filter(owner=self.value())


##############################
class CustomModelAdmin(admin.ModelAdmin):

	def logi(self, *args):
		msg = f'ℹ️{self.__class__.__name__}.{sys._getframe().f_back.f_code.co_name}'
		for arg in args:
			msg += f'::{arg}'
		logging.info(msg)

	def logw(self, *args):
		msg = f'⚠{self.__class__.__name__}.{sys._getframe().f_back.f_code.co_name}'
		for arg in args:
			msg += f'::{arg}'
		logging.warning(msg)

	def loge(self, err, *args):
		msg = f'🆘{self.__class__.__name__}.{err.__traceback__.tb_frame.f_code.co_name}::{err}::LINE={err.__traceback__.tb_lineno}'
		for arg in args:
			msg += f'::{arg}'
		logging.error(msg)


class LogEntryAdmin(admin.ModelAdmin):
	list_display = ('id', 'action_time', 'user', 'content_type', 'object_repr', 'action_flag', 'change_message')
	search_fields = ('id', 'action_time', 'user__username', 'user__first_name', 'user__last_name', 'user__email', 'object_repr', 'change_message')
admin.site.register(LogEntry, LogEntryAdmin)


class DeviceTypeAdmin(CustomModelAdmin):
	list_display = ('id', 'name', 'description')
	list_display_links = ['name']
	search_fields = ['id', 'name', 'description']
admin.site.register(DeviceType, DeviceTypeAdmin)



class TZForm(forms.ModelForm):
	tz = forms.ChoiceField(widget=Select2Widget, choices=[(t, t) for t in sorted(available_timezones())])


class UploadFileForm(forms.Form):
	_selected_action = forms.CharField(widget=forms.MultipleHiddenInput)
	file = forms.FileField(widget=forms.ClearableFileInput(attrs={'multiple': True}))


class NotificationSourceGroupAdmin(CustomModelAdmin):
	list_display = ('id', 'name', 'description')
	list_display_links = ('id', 'name',)
	search_fields = ('name', 'description')
admin.site.register(NotificationSourceGroup, NotificationSourceGroupAdmin)


class NotificationSourceAdmin(CustomModelAdmin):
	list_display = ('id', 'name', 'value', 'description', 'group')
	list_display_links = ('id', 'name',)
	search_fields = ('value', 'name', 'description', 'group__name', 'group__description')
admin.site.register(NotificationSource, NotificationSourceAdmin)


class NotificationTypeAdmin(CustomModelAdmin):
	list_display = ('id', 'value', 'name')
	list_display_links = ('id', 'name',)
	search_fields = ('id', 'value', 'name')
admin.site.register(NotificationType, NotificationTypeAdmin)


class NotificationTemplateAdmin(CustomModelAdmin):
	list_display = ('id', 'get_source', 'get_type')
	list_display_links = ('id',)
	search_fields = ('source__name', 'notification_type__name', 'notification_type__value', 'body')

	def get_source(self, obj):
		o = obj.source
		m = o._meta
		return format_html('''<p><font color="green" face="Verdana, Geneva, sans-serif"><a href="{}" target="_blank">{}</a></font></p>''', reverse('admin:{}_{}_change'.format(m.app_label, m.model_name), args=(o.id,)), o.name)
	get_source.short_description = _('source')
	get_source.admin_order_field = 'source'

	def get_type(self, obj):
		o = obj.notification_type
		m = o._meta
		return format_html('''<p><font color="green" face="Verdana, Geneva, sans-serif"><a href="{}" target="_blank">{}</a></font></p>''', reverse('admin:{}_{}_change'.format(m.app_label, m.model_name), args=(o.id,)), o.name)
	get_type.short_description = _('notification_type')
	get_type.admin_order_field = 'notification_type'

admin.site.register(NotificationTemplate, NotificationTemplateAdmin)


class NotificationOptionAdmin(CustomModelAdmin):
	list_display = ('id', 'source', 'get_owner', 'get_types')
	list_display_links = ['id']
	search_fields = ('source__name', 'owner__username', 'owner__first_name', 'owner__last_name', 'owner__email')
	list_select_related = ('source', 'owner')
	list_filter = [NotificationSourceFilter, OwnerFilter, 'types']
	autocomplete_fields = ['source', 'owner', 'types']
	list_editable = ['source']
	actions = ['reset_all_types']

	def get_queryset(self, request):
		qs = super().get_queryset(request)
		user = request.user
		if user.is_superuser:
			return qs
		return qs.filter(owner=user)

	def get_owner(self, obj):
		o = obj.owner
		if o:
			m = o._meta
			return format_html('''<p><font color="green" face="Verdana, Geneva, sans-serif"><a href="{}" target="_blank">{}</a></font></p>''', reverse('admin:{}_{}_change'.format(m.app_label, m.model_name), args=(o.id,)), o.username)
		else:
			return ''
	get_owner.short_description = _('owner')
	get_owner.admin_order_field = 'owner'

	def get_types(self, obj):
		return format_html_join('\n', '<p><font size="+1" color="green" face="Verdana, Geneva, sans-serif">{}</font></p>', obj.types.values_list('name'))
	get_types.short_description = _('types')
	get_types.admin_order_field = 'types'

	def reset_all_types(self, request, queryset):
		for item in queryset:
			try:
				item.types.clear()
			except Exception as e:
				self.loge(e)
	reset_all_types.short_description = _('reset all types')

admin.site.register(NotificationOption, NotificationOptionAdmin)


class NotificationDelayAdmin(CustomModelAdmin):
	list_display = ('id', 'source', 'owner', 'interval')
	list_display_links = ('id', 'source',)
	search_fields = ('source__name', 'owner__username', 'owner__first_name', 'owner__last_name', 'owner__email', 'interval')
	list_select_related = ('source']
	list_filter = ('source',)
admin.site.register(NotificationDelay, NotificationDelayAdmin)


class NotificationTaskAdmin(CustomModelAdmin):
	list_display = ('id', 'created_at', 'send_after', 'sended_at', 'get_source', 'get_type', 'get_target_user', 'response', 'subject', 'content', 'entity', 'description', 'reason')
	list_display_links = ['id']
	search_fields = ('id', 'created_at', 'send_after', 'sended_at', 'source__name', 'target_user__username', 'target_user__first_name', 'target_user__last_name', 'target_user__email', 'notification_type__name', 'response', 'subject', 'content', 'entity', 'description', 'reason')
	list_select_related = ('source', 'notification_type')
	list_filter = ('source', 'notification_type')

	def get_source(self, obj):
		o = obj.source
		m = o._meta
		return format_html('''<p><font color="green" face="Verdana, Geneva, sans-serif"><a href="{}" target="_blank">{}</a></font></p>''', reverse('admin:{}_{}_change'.format(m.app_label, m.model_name), args=(o.id,)), o.name)
	get_source.short_description = _('source')
	get_source.admin_order_field = 'source'

	def get_type(self, obj):
		o = obj.notification_type
		m = o._meta
		return format_html('''<p><font color="green" face="Verdana, Geneva, sans-serif"><a href="{}" target="_blank">{}</a></font></p>''', reverse('admin:{}_{}_change'.format(m.app_label, m.model_name), args=(o.id,)), o.name)
	get_type.short_description = _('notification_type')
	get_type.admin_order_field = 'notification_type'

	def get_target_user(self, obj):
		o = obj.target_user
		if o:
			m = o._meta
			return format_html('''<p><font color="green" face="Verdana, Geneva, sans-serif"><a href="{}" target="_blank">{}</a></font></p>''', reverse('admin:{}_{}_change'.format(m.app_label, m.model_name), args=(o.id,)), o.username)
		else:
			return ''
	get_target_user.short_description = _('target_user')
	get_target_user.admin_order_field = 'target_user'

admin.site.register(NotificationTask, NotificationTaskAdmin)


class NotificationBulkEmailAdmin(CustomModelAdmin):
	list_display = ('id', 'name', 'emails', 'notifications')
	list_display_links = ('id', 'name')
	search_fields = ('name', 'emails', 'notifications')

admin.site.register(NotificationBulkEmail, NotificationBulkEmailAdmin)

