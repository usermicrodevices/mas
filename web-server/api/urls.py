app_name = 'api'

from django.urls import path, include
from rest_framework.routers import DefaultRouter

import rest_framework_jwt.views

from . import views

from users.views import RoleViewSet, UserViewSet

#from notifications.views import NotificationSourceGroupViewSet, NotificationSourceViewSet, NotificationTypeViewSet, NotificationTemplateViewSet, NotificationOptionViewSet, NotificationDelayViewSet, NotificationBulkEmailViewSet

from core.views import OwnerViewSet, TagViewSet, DeviceTypeViewSet, DeviceGroupViewSet, DeviceViewSet, HistoryViewSet

router_refs = DefaultRouter()
router_refs.register('roles', RoleViewSet)
router_refs.register('users', UserViewSet)
router_refs.register('devicetypes', DeviceTypeViewSet)
router_refs.register('devicegroups', DeviceGroupViewSet)
#router_refs.register('notificationsourcegroups', NotificationSourceGroupViewSet)
#router_refs.register('notificationsources', NotificationSourceViewSet)
#router_refs.register('notificationtypes', NotificationTypeViewSet)
#router_refs.register('notificationtemplates', NotificationTemplateViewSet)

router = DefaultRouter()
router.register('owners', OwnerViewSet, basename='owner')
router.register('tags', TagViewSet, basename='tag')
router.register('devices', DeviceViewSet, basename='device')
router.register('histories', HistoryViewSet, basename='history')
#router.register('notificationoptions', NotificationOptionViewSet, basename='notificationoption')

urlpatterns = [
	path('', views.index, name='index'),
	path('version', views.handle_version),
	path('user', views.get_current_user),
	path('login', rest_framework_jwt.views.obtain_jwt_token),
	path('verify_token', rest_framework_jwt.views.verify_jwt_token),
	path('refresh_token', rest_framework_jwt.views.refresh_jwt_token),
	path('refs/', include(router_refs.urls)),
	path('data/', include(router.urls)),
	path('api-auth/', include('rest_framework.urls'))
]
