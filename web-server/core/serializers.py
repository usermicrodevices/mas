import logging, sys

from drf_writable_nested.serializers import WritableNestedModelSerializer

from .models import Owner, Tag, DeviceType, DeviceGroup, Device, History


class BaseCustomSerializer(WritableNestedModelSerializer):
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


class OwnerSerializer(BaseCustomSerializer):
	class Meta:
		model = Owner
		fields = '__all__'


class TagSerializer(BaseCustomSerializer):
	class Meta:
		model = Tag
		fields = '__all__'


class DeviceTypeSerializer(BaseCustomSerializer):
	class Meta:
		model = DeviceType
		fields = '__all__'


class DeviceGroupSerializer(BaseCustomSerializer):
	class Meta:
		model = DeviceGroup
		fields = '__all__'


class DeviceSerializer(BaseCustomSerializer):
	group = DeviceGroupSerializer()
	type = DeviceTypeSerializer()
	class Meta:
		model = Device
		fields = '__all__'


class HistorySerializer(BaseCustomSerializer):
	device = DeviceSerializer()
	owner = OwnerSerializer()
	class Meta:
		model = History
		fields = '__all__'
