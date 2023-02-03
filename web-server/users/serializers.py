import json, logging, os, sys

from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.models import AnonymousUser, Group

from drf_writable_nested.serializers import WritableNestedModelSerializer

from .models import Role, User


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


class GroupSerializer(BaseCustomSerializer):
	class Meta:
		model = Group
		fields = '__all__'


class RoleSerializer(BaseCustomSerializer):
	class Meta:
		model = Role
		fields = '__all__'


class UserSerializer(BaseCustomSerializer):

	class Meta:
		model = User
		fields = '__all__'
		extra_kwargs = {'password':{'write_only':True}, 'is_superuser':{'read_only':True}, 'is_staff':{'read_only':True}, 'groups':{'read_only':True}, 'user_permissions':{'read_only':True}}

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

	def validate_password(self, value: str) -> str:
		user = self.context['request'].user
		validate_password(value, user)
		return value

	def create(self, validated_data):
		if 'role' not in validated_data:
			anon = AnonymousUser()
			anon.username = 'Role is not setup'
			return anon
		if 'groups' not in validated_data:
			validated_data['groups'] = [validated_data['role'].group]
		if 'username' not in validated_data or not validated_data['username']:
			self.logw('MAIN FIELD IS EMPTY', validated_data)
			anon = AnonymousUser()
			anon.username = 'Main field not setup'
			return anon
		password = validated_data.pop('password')
		user = super().create(validated_data)
		user.set_password(password)
		user.save()
		return user

	def update(self, instance, validated_data):
		if 'password' in validated_data:
			password = validated_data.pop('password')
			instance.set_password(password)
			instance.save()
		return super().update(instance, validated_data)


class UserNameSerializer(BaseCustomSerializer):
	class Meta:
		model = User
		fields = ['id', 'username', 'first_name','last_name']
