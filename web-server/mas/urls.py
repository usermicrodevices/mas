from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.views.generic.base import RedirectView
from django.utils.translation import gettext as _
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from rest_framework.permissions import AllowAny
from rest_framework.schemas import get_schema_view
from rest_framework_swagger.renderers import SwaggerUIRenderer, OpenAPIRenderer

urlpatterns = [
	path('favicon.ico', RedirectView.as_view(url=settings.STATIC_URL + 'favicon.ico')),
	path('api/admin/', admin.site.urls),
	path('api/', include('api.urls')),
	path('api/help/', get_schema_view(title='MAS', description='API for all things …', version='1.0.0', renderer_classes=[OpenAPIRenderer, SwaggerUIRenderer], permission_classes=[AllowAny]), name='openapi-schema'),
	path('select2/', include('django_select2.urls')),
]

urlpatterns += staticfiles_urlpatterns()

admin.site.index_title = f'''🖥️{_('MAS')}🖥️'''
admin.site.site_title = f'''🖥️{_('mas')}🖥️'''
admin.site.site_header = f'''🖥️{_('Machine accounting system')}🖥️'''
admin.site.subtitle = 'mas'
