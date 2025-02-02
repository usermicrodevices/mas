import asyncio, csv, json, logging, os, threading, sys, xlsxwriter
from time import time, sleep
from datetime import timedelta, datetime
from io import BytesIO, StringIO
from asgiref.sync import sync_to_async
from pyexcelerate import Workbook
try:
	from zoneinfo import ZoneInfo
except:
	from backports.zoneinfo import ZoneInfo

from django.conf import settings

from django.utils import timezone
from django.utils.translation import gettext as _
from django.http import Http404, JsonResponse, HttpResponseNotFound, FileResponse, HttpResponse, StreamingHttpResponse, HttpResponseServerError, HttpResponseForbidden
from django.db import connection
from django.db.utils import IntegrityError
from django.db.models import F, Q, Avg, Sum, Count, Value, IntegerField, FloatField, DecimalField, Case, When, Max, Min, ForeignKey, CASCADE, Window, Exists, OuterRef
from django.db.models.query import QuerySet
from django.db.models.functions import Coalesce, TruncMinute, TruncHour, TruncDay, TruncWeek, TruncMonth, TruncQuarter, ExtractDay, RowNumber, Round
from django.db.models.expressions import RawSQL
from django.shortcuts import get_object_or_404, get_list_or_404
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.core.cache import caches

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets, filters
from rest_framework.decorators import action, authentication_classes, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import BasePermission, IsAuthenticated, IsAuthenticatedOrReadOnly, SAFE_METHODS, DjangoModelPermissions, AllowAny

from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_cookie

from .models import Owner, Tag, DeviceType, DeviceGroup, Device, History

from users.models import RoleField

from .serializers import OwnerSerializer, TagSerializer, DeviceTypeSerializer, DeviceGroupSerializer, DeviceSerializer, HistorySerializer


class IsOwnerOrReadOnly(BasePermission):
	def has_permission(self, request, view):
		return request.method in SAFE_METHODS
	def has_object_permission(self, request, view, obj):
		if request.method in permissions.SAFE_METHODS:
			return True
		return obj.author == request.user


class AppBaseViewSet(viewsets.ModelViewSet):
	permission_classes = [IsAuthenticatedOrReadOnly, DjangoModelPermissions]
	pagination_class = LimitOffsetPagination
	filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
	ordering_fields = '__all__'
	filterset_fields = '__all__'

	def logi(self, *args):
		msg = f'ℹ️{self.__class__.__name__}.{sys._getframe().f_back.f_code.co_name}'
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

	@action(detail=False, methods=['get', ], url_path='permissions')
	def handle_permissions(self, request):
		model_name = self.serializer_class.Meta.model.__name__
		rfields = RoleField.objects.filter(role = request.user.role, role_model__value = model_name)
		model_name_lower = model_name.lower()
		p = Permission.objects.filter(Q(group__in=request.user.groups.all()) | Q(user=request.user)).filter(content_type__app_label=self.serializer_class.Meta.model._meta.app_label, content_type__model=model_name_lower).distinct()
		actions = [x.codename if not x.codename.endswith('_'+model_name_lower) else x.codename[:-len(model_name_lower)-1] for x in p]
		response_data = {'fields':{f.value:{'read':f.read, 'write':f.write} for f in rfields}, 'actions':actions}
		return Response(response_data)

	def send_link_to_email(self, email_str, link, now_str, subject_prefix=None):
		if not subject_prefix:
			subject_prefix = self.queryset.model._meta.verbose_name_plural
		subject = ''
		if subject_prefix:
			subject += f'{subject_prefix} '
		subject += f'{now_str}'
		email_message = f'<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8"><title>{subject}</title></head><body><a href="{link}">{subject}</a></body></html>'
		try:
			mail_response = send_mail(subject, '', '', (email_str,), html_message=email_message)
		except Exception as e:
			self.loge(e)
		else:
			self.logi(mail_response, email_str, subject, link)


class OwnerViewSet(AppBaseViewSet):
	serializer_class = OwnerSerializer
	queryset = Owner.objects.filter(active=True)


class TagViewSet(AppBaseViewSet):
	serializer_class = TagSerializer
	queryset = Tag.objects.all()


class DeviceTypeViewSet(AppBaseViewSet):
	serializer_class = DeviceTypeSerializer
	queryset = DeviceType.objects.all()


class DeviceGroupViewSet(AppBaseViewSet):
	serializer_class = DeviceGroupSerializer
	queryset = DeviceGroup.objects.all()


class DeviceViewSet(AppBaseViewSet):
	cache_devices = caches['devices']
	serializer_class = DeviceSerializer
	queryset = Device.objects.none()
	filterset_fields = ['id',  'created_date']
	search_fields = ['id',  'created_date']

	def get_queryset(self):
		kwargs = {}
		for k, v in self.request.query_params.items():
			if '_id__in' in k:
				try:
					kwargs[k] = [int(i) for i in v.split(',')]
				except Exception as e:
					self.loge(e)
			elif '__range' in k or '__in' in k:
				kwargs[k] = v.split(',')
			elif k not in ('limit', 'offset', 'ordering', 'search', 'format', 'next', 'subtitle'):
				kwargs[k] = v
		current_user = self.request.user
		if current_user.is_superuser:
			return Device.objects.filter(**kwargs)
		if not current_user.role:
			self.logw('ROLE IS EMPTY', current_user)
		return Device.objects.filter(**kwargs).distinct()

	def accessed_queryset_beverages(self, request):
		current_user = request.user
		if current_user.is_superuser:
			return Beverage.objects.all()
		else:
			return Beverage.objects.filter(Q(device__sale_point__company__in=current_user.companies.all()) | Q(device__sale_point__in=current_user.sale_points.all())).filter(~Q(device__sale_point__status_reference_id=2)).distinct()


class HistoryViewSet(AppBaseViewSet):
	serializer_class = HistorySerializer
	queryset = History.objects.all()
