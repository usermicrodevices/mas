import logging, sys

from django.core.cache import caches
from django.db.models import Q
from django.contrib.auth.models import Group, Permission

from rest_framework import viewsets, filters
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.response import Response

from django_filters.rest_framework import DjangoFilterBackend

from .models import Role, User
from .serializers import RoleSerializer, UserSerializer, GroupSerializer


class GroupViewSet(viewsets.ModelViewSet):
	serializer_class = GroupSerializer
	queryset = Group.objects.all()


class RoleViewSet(viewsets.ModelViewSet):
	permission_classes = [DjangoModelPermissions]
	filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
	serializer_class = RoleSerializer
	queryset = Role.objects.none()
	pagination_class = LimitOffsetPagination

	def get_queryset(self):
		try:
			return Role.objects.filter(weight__gte=self.request.user.role.weight)
		except Exception as e:
			return Role.objects.none()


class UserViewSet(viewsets.ModelViewSet):
	cache = caches['users']
	permission_classes = [DjangoModelPermissions]
	filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
	serializer_class = UserSerializer
	queryset = User.objects.none()
	pagination_class = LimitOffsetPagination

	def get_queryset(self):
		kwargs = self.request.parser_context.get('kwargs', {})
		user = self.request.user
		try:
			pk_int = int(kwargs.get('pk', -1))
		except:
			pk_int = -1
		if pk_int == user.id:
			return User.objects.filter(pk=pk_int)
		elif user.is_superuser:
			return User.objects.all()
		else:
			perms = user.get_all_permissions()
			conditions = Q(pk=user.id)
			#if 'users.can_view_users_by_extinfo' in perms:
				#conditions |= Q(extinfo__flag=True)
			exclude_conditions = Q(role__weight__lt=user.role.weight) | Q(is_staff=True) | Q(is_superuser=True)
			return User.objects.filter(conditions).exclude(exclude_conditions).distinct()
		return User.objects.none()

	def list(self, request):
		cache_key = f'{request.user.id}'
		result = self.cache.get(cache_key)
		if not result:
			queryset = self.filter_queryset(self.get_queryset())
			serializer = self.serializer_class(queryset, many=True)
			result = serializer.data
			if self.cache.has_key(cache_key):
				self.cache.set(cache_key, result)
			else:
				self.cache.add(cache_key, result)
		return Response(result)
