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

from .models import CustomAbstractModel, DeviceType, Device

from users.models import User

list_models = inspect.getmembers(sys.modules['core.models'], inspect.isclass)
exclude_classes = [CustomAbstractModel, DeviceType, Device, User]

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
class TZForm(forms.ModelForm):
	tz = forms.ChoiceField(widget=Select2Widget, choices=[(t, t) for t in sorted(available_timezones())])
class UploadFileForm(forms.Form):
	_selected_action = forms.CharField(widget=forms.MultipleHiddenInput)
	file = forms.FileField(widget=forms.ClearableFileInput(attrs={'multiple': True}))


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
	list_display = ['id', 'action_time', 'user', 'content_type', 'object_repr', 'action_flag', 'change_message']
	search_fields = ['id', 'action_time', 'user__username', 'user__first_name', 'user__last_name', 'user__email', 'object_repr', 'change_message']
admin.site.register(LogEntry, LogEntryAdmin)


class OwnerAdmin(CustomModelAdmin):
	list_display = ['id', 'name', 'family', 'patronymic', 'domain', 'login', 'active']
	list_display_links = ['id', 'name']
	search_fields = ['id', 'name', 'family', 'patronymic', 'domain', 'login', 'active']
admin.site.register(Owner, OwnerAdmin)


class TagAdmin(CustomModelAdmin):
	list_display = ['id', 'name', 'weight']
	list_display_links = ['id', 'name']
	search_fields = ['id', 'name', 'weight']
admin.site.register(Tag, TagAdmin)


class DeviceTypeAdmin(CustomModelAdmin):
	list_display = ['id', 'name', 'description']
	list_display_links = ['id', 'name']
	search_fields = ['id', 'name', 'description']
admin.site.register(DeviceType, DeviceTypeAdmin)


class DeviceGroupAdmin(CustomModelAdmin):
	list_display = ['id', 'name', 'parent']
	list_display_links = ['id', 'name']
	search_fields = ['id', 'name']
admin.site.register(DeviceGroup, DeviceGroupAdmin)


class DeviceAdmin(CustomModelAdmin):
	list_display = ['id', 'extinfo', 'group', 'device_model', 'created', 'status']
	list_display_links = ['id', 'extinfo']
	search_fields = ['id', 'created', 'extinfo', 'group__name']
admin.site.register(Device, DeviceAdmin)


class HistoryAdmin(CustomModelAdmin):
	list_display = ['id', 'created', 'closed', 'group', 'device_model', 'status']
	list_display_links = ['id', 'extinfo']
	search_fields = ['id', 'created', 'closed', 'extinfo', 'group__name']
admin.site.register(History, HistoryAdmin)

