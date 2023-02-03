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
from django.contrib.auth.models import Group, Permission
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

from .models import NotificationSource, NotificationType, NotificationTemplate, NotificationSourceGroup, NotificationOption, NotificationDelay, NotificationBulkEmail

from users.models import RoleField

from .serializers import NotificationSourceSerializer, NotificationTypeSerializer, NotificationTemplateSerializer, NotificationSourceGroupSerializer, NotificationOptionSerializer, NotificationDelaySerializer, NotificationBulkEmailSerializer


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


class NotificationSourceGroupViewSet(AppBaseViewSet):
	serializer_class = NotificationSourceGroupSerializer
	queryset = NotificationSourceGroup.objects.all()
	filterset_fields = ['id', 'name', 'description']
	search_fields = ['id', 'name', 'description']


class NotificationSourceViewSet(AppBaseViewSet):
	serializer_class = NotificationSourceSerializer
	queryset = NotificationSource.objects.all()
	filterset_fields = ['id', 'value', 'name', 'description', 'group__id']
	search_fields = ['id', 'value', 'name', 'description', 'group__name', 'group__description']

	def get_queryset(self):
		current_user = self.request.user
		if current_user.is_superuser:
			return NotificationSource.objects.all()
		else:
			return NotificationSource.objects.filter(group_id=1)


class NotificationTypeViewSet(AppBaseViewSet):
	serializer_class = NotificationTypeSerializer
	queryset = NotificationType.objects.all()
	filterset_fields = ['id', 'value', 'name']
	search_fields = ['id', 'value', 'name']


class NotificationTemplateViewSet(AppBaseViewSet):
	serializer_class = NotificationTemplateSerializer
	queryset = NotificationTemplate.objects.all()
	filterset_fields = ['id', 'source', 'body', 'notification_type__id']
	search_fields = ['id', 'source', 'body', 'notification_type__value', 'notification_type__name']


class NotificationOptionViewSet(AppBaseViewSet):
	serializer_class = NotificationOptionSerializer
	queryset = NotificationOption.objects.none()
	filterset_fields = ['id', 'source', 'owner', 'types__id']
	search_fields = ['id', 'source', 'owner__username', 'owner__first_name', 'owner__last_name', 'owner__email', 'types__value', 'types__name']

	def get_queryset(self):
		current_user = self.request.user
		if current_user.is_superuser:
			return NotificationOption.objects.all()
		else:
			return NotificationOption.objects.filter(owner_id=current_user.id, source__group_id=1)

	@action(detail=False, methods=['get'])
	def current(self, request):
		ser = self.serializer_class(self.get_queryset(), many = True)
		return Response(ser.data)

	def perform_create(self, serializer):
		serializer.save(owner=self.request.user)


class NotificationDelayViewSet(AppBaseViewSet):
	serializer_class = NotificationDelaySerializer
	queryset = NotificationDelay.objects.none()
	filterset_fields = ['id', 'source', 'owner', 'interval']
	search_fields = ['id', 'source', 'owner__username', 'owner__first_name', 'owner__last_name', 'owner__email', 'interval']

	def get_queryset(self):
		current_user = self.request.user
		if current_user.is_superuser:
			return NotificationDelay.objects.all()
		else:
			return NotificationDelay.objects.filter(owner_id=current_user.id)

	@action(detail=False, methods=['get'])
	def current(self, request):
		ser = self.serializer_class(self.get_queryset(), many = True)
		return Response(ser.data)

	def perform_create(self, serializer):
		serializer.save(owner=self.request.user)


class NotificationBulkEmailViewSet(AppBaseViewSet):
	serializer_class = NotificationBulkEmailSerializer
	queryset = NotificationBulkEmail.objects.none()
	filterset_fields = ['id',  'name', 'emails']
	search_fields = ['id', 'name', 'emails', 'notifications']
