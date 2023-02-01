app_name = 'api'

from django.urls import path, include
from rest_framework.routers import DefaultRouter

import rest_framework_jwt.views

from . import views

from core.views import EquipmentViewSet

from users.views import RoleViewSet, UserViewSet

router_refs = DefaultRouter()
router_refs.register('roles', RoleViewSet)
router_refs.register('users', UserViewSet)

router = DefaultRouter()
router.register('equipments', EventViewSet, basename='equipment')

urlpatterns = [
	path('', views.index, name='index'),
	path('privacy', views.url_privacy, name='url_privacy'),
	path('version', views.handle_version),
	path('user', views.get_current_user),
	path('login', rest_framework_jwt.views.obtain_jwt_token),
	path('verify_token', rest_framework_jwt.views.verify_jwt_token),
	path('refresh_token', rest_framework_jwt.views.refresh_jwt_token),
	path('refs/', include(router_refs.urls)),
	path('data/', include(router.urls)),
	path('api-auth/', include('rest_framework.urls'))
]
