import logging, sys

from django.contrib.auth import get_user_model
User = get_user_model()

from rest_framework import serializers
from drf_serializer_cache import SerializerCacheMixin

from drf_writable_nested.serializers import WritableNestedModelSerializer

from .models import DeviceType, Device, NotificationSource, NotificationType, NotificationTemplate, NotificationSourceGroup, NotificationOption, NotificationDelay, NotificationBulkEmail, Tag


class BaseCustomSerializer(serializers.ModelSerializer):
	def logi(self, *args):
		msg = f'{self.__class__.__name__}.{sys._getframe().f_back.f_code.co_name}'
		for arg in args: msg += f'::{arg}'
		logging.info(msg)
	def logw(self, *args):
		msg = f'{self.__class__.__name__}.{sys._getframe().f_back.f_code.co_name}'
		for arg in args: msg += f'::{arg}'
		logging.warning(msg)
	def loge(self, err, *args):
		msg = f'{self.__class__.__name__}.{err.__traceback__.tb_frame.f_code.co_name}::{err}::LINE={err.__traceback__.tb_lineno}'
		for arg in args: msg += f'::{arg}'
		logging.error(msg)


class DeviceTypeSerializer(SerializerCacheMixin, serializers.ModelSerializer):
	class Meta:
		model = DeviceType
		fields = '__all__'


class DeviceSerializer(SerializerCacheMixin, serializers.ModelSerializer):
	class Meta:
		model = Device
		fields = '__all__'


class UserSerializer(serializers.ModelSerializer):
	class Meta:
		model = User
		exclude = ['id', 'password', 'user_permissions']


class UserNameSerializer(serializers.ModelSerializer):
	class Meta:
		model = User
		fields = ['id', 'username', 'first_name','last_name']


class NotificationSourceGroupSerializer(SerializerCacheMixin, serializers.ModelSerializer):
	class Meta:
		model = NotificationSourceGroup
		fields = '__all__'


class NotificationSourceSerializer(SerializerCacheMixin, serializers.ModelSerializer):
	class Meta:
		model = NotificationSource
		fields = '__all__'


class NotificationTypeSerializer(SerializerCacheMixin, serializers.ModelSerializer):
	class Meta:
		model = NotificationType
		fields = '__all__'


class NotificationTemplateSerializer(SerializerCacheMixin, serializers.ModelSerializer):
	class Meta:
		model = NotificationTemplate
		fields = '__all__'


class NotificationOptionSerializer(SerializerCacheMixin, serializers.ModelSerializer):
	class Meta:
		model = NotificationOption
		fields = '__all__'


class NotificationDelaySerializer(SerializerCacheMixin, serializers.ModelSerializer):
	class Meta:
		model = NotificationDelay
		fields = '__all__'


class NotificationBulkEmailSerializer(WritableNestedModelSerializer):
	notifications = serializers.JSONField(required=False, initial=list)
	class Meta:
		model = NotificationBulkEmail
		fields = '__all__'


class TagSerializer(BaseCustomSerializer):
	class Meta:
		model = Tag
		fields = '__all__'
