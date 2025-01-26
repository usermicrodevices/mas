import os, datetime
import mas.middleware
import django
django.utils.encoding.smart_text = django.utils.encoding.smart_str
django.utils.translation.ugettext = django.utils.translation.gettext

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SILENCED_SYSTEM_CHECKS = ['urls.W002', 'security.W019']

SECRET_KEY = 'elnp@jog$z_2b#9t4n-6xy$+lwjqrmt3os5t#_sshm*un)f8y7'

DEBUG = False

HOST = 'mas.work'
HOST_STAGE = f'stage.{HOST}'

ALLOWED_HOSTS = ['127.0.0.1', 'localhost', '192.168.0.1', HOST, f'api.{HOST}', HOST_STAGE]

DEFAULT_FROM_EMAIL = f'admin@{HOST}'

INSTALLED_APPS = [
'api.apps.ApiConfig',
'users.apps.UsersConfig',
'core.apps.CoreConfig',
'django.contrib.admin',
'django.contrib.auth',
'django.contrib.contenttypes',
'django.contrib.sessions',
'django.contrib.messages',
'django.contrib.staticfiles',
'rest_framework',
'rest_framework_swagger',
'corsheaders',
'drf_serializer_cache',
'push_notifications',
'django_apscheduler',
'django_filters',
'django_select2',
]

MIDDLEWARE = [
'corsheaders.middleware.CorsMiddleware',
'django.middleware.security.SecurityMiddleware',
'django.contrib.sessions.middleware.SessionMiddleware',
'django.middleware.common.CommonMiddleware',
'django.middleware.csrf.CsrfViewMiddleware',
'django.contrib.auth.middleware.AuthenticationMiddleware',
'django.contrib.messages.middleware.MessageMiddleware',
'django.middleware.clickjacking.XFrameOptionsMiddleware',
'django.middleware.locale.LocaleMiddleware',
'mas.middleware.TimezoneMiddleware',
#'corsheaders.middleware.CorsPostCsrfMiddleware',
'crum.CurrentRequestUserMiddleware'
]

LOGOUT_URL = '/api/admin/logout/'

ROOT_URLCONF = 'mas.urls'

TEMPLATES = [
	{
		'BACKEND': 'django.template.backends.django.DjangoTemplates',
		'OPTIONS': {
			'libraries': {'staticfiles':'django.templatetags.static'},
			'context_processors': [
				'django.template.context_processors.media',
				'django.template.context_processors.debug',
				'django.template.context_processors.request',
				'django.contrib.auth.context_processors.auth',
				'django.contrib.messages.context_processors.messages',
			],
			'loaders': [
				('django.template.loaders.cached.Loader', [
					'django.template.loaders.filesystem.Loader',
					'django.template.loaders.app_directories.Loader',
				]),
				('django.template.loaders.locmem.Loader', {
					'dropdown_filter_from_memory.html': '''{%load i18n%}<script type="text/javascript">var $=django.jQuery; var jQuery=django.jQuery; var go_from_select=function(opt){window.location=window.location.pathname+opt;}; $(document).ready(function(){try{$(".second-style-selector").select2();}catch(e){console.log(e);};});</script><h3>{%blocktrans with title as filter_title%} By {{filter_title}} {%endblocktrans %}</h3><ul class="admin-filter-{{title|cut:' '}}">{%if choices|slice:"4:"%}<li><select class="form-control second-style-selector" style="width:95%;margin-left:2%;" onchange="go_from_select(this.options[this.selectedIndex].value)">{%for choice in choices%}<option {%if choice.selected%} selected="selected"{%endif%} value="{{choice.query_string|iriencode}}">{{choice.display}}</option>{%endfor%}</select></li>{% else%}{%for choice in choices%}<li {%if choice.selected%} class="selected"{%endif%}><a href="{{choice.query_string|iriencode}}">{{choice.display}}</a></li>{%endfor%}{%endif%}</ul>''',
					'admin_select_file_form.html':'''{%extends "admin/base_site.html"%}{%block content%}<form enctype="multipart/form-data" action="" method="post">{%csrf_token%}{{form}}<ul>{{items|unordered_list}}</ul><input type="hidden" name="action" value="{{current_action}}" /><input type="submit" name="apply" value="Save" /><button onclick="window.location.href='{{request.path}}'">GoBack</button></form>{%endblock%}'''
				}),
			],
		},
	},
]

WSGI_APPLICATION = 'mas.wsgi.application'

DATABASES = {
	'default': {
		'ENGINE': 'django.db.backends.postgresql',
		'NAME': 'mas',
		'USER': 'your_login',
		'PASSWORD': 'your_password',
		'HOST': '127.0.0.1',
		'PORT': '5432',
		'OPTIONS':{'connect_timeout':1}
	}
}

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

DATA_UPLOAD_MAX_NUMBER_FIELDS = 102400

CACHES = {
	'default':{'BACKEND':'django.core.cache.backends.locmem.LocMemCache', 'OPTIONS':{'MAX_ENTRIES':99999999, 'CULL_FREQUENCY':99999998}},
	'notifications':{'BACKEND':'django.core.cache.backends.locmem.LocMemCache', 'LOCATION':'notifications', 'TIMEOUT':300, 'OPTIONS':{'MAX_ENTRIES':99999999, 'CULL_FREQUENCY':99999998}},
	'users':{'BACKEND':'django.core.cache.backends.locmem.LocMemCache', 'LOCATION':'users', 'TIMEOUT':86400, 'OPTIONS':{'MAX_ENTRIES':99999999, 'CULL_FREQUENCY':99999998}},
	'devices':{'BACKEND':'django.core.cache.backends.locmem.LocMemCache', 'LOCATION':'users', 'TIMEOUT':86400, 'OPTIONS':{'MAX_ENTRIES':99999999, 'CULL_FREQUENCY':99999998}}
}

AUTH_PASSWORD_VALIDATORS = [
	{
		'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
	},
	{
		'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
	},
	{
		'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
	},
	{
		'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
	},
]

from django.utils.translation import gettext_lazy as _
LOCALE_PATHS = [os.path.join(BASE_DIR, 'locale')]
LANGUAGES = [('en', _('English')), ('ru', _('Russian'))]

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

MEDIA_ROOT = 'media/'

STATIC_URL = '/api/static/'
STATIC_ROOT = 'static'

CSRF_COOKIE_AGE = 600
CSRF_TRUSTED_ORIGINS = [f'https://{HOST}', f'https://{HOST_STAGE}']

LOGGING = {
	'version': 1,
	'disable_existing_loggers': False,
	'formatters': {
		'verbose': {
			'format': '[{levelname:1.1}] | {asctime} | {module} > {message}',
			'style': '{',
			'datefmt': '%Y-%m-%d %H:%M:%S'
		}
	},
	'filters': {
		'require_debug_true': {
			'()': 'django.utils.log.RequireDebugTrue',
		},
	},
	'handlers': {
		'file': {
			'level':'DEBUG',
			'class':'logging.handlers.TimedRotatingFileHandler',
			'filename':'logs/server.log',
			'formatter':'verbose',
			'backupCount':31,
			'when':'midnight'
		},
		'console': {
			'level': 'INFO',
			'class': 'logging.StreamHandler',
			'filters': ['require_debug_true',],
			'formatter': 'verbose'
		}
	},
	'loggers': {
		'django': {
			'handlers': ['file', 'console'],
			'level': 'DEBUG',
			'propagate': False,
		},
		'django.utils.autoreload': {
			'handlers': ['file', 'console'],
			'level': 'WARNING',
		},
		'': {
			'handlers': ['file', 'console'],
			'level': 'DEBUG',
		},
		'asyncio': {
			'level': 'WARNING',
		},
		'django.server': {
			'level': 'ERROR',
			'propagate': False
		},
		'daphne': {
			'handlers': ['console'],
			'level': 'ERROR'
		},
		'apscheduler': {
			'handlers': ['file', 'console'],
			'level': 'ERROR'
		},
		'apscheduler.executors': {
			'handlers': ['file', 'console'],
			'level': 'ERROR'
		},
		'apscheduler.jobstores': {
			'handlers': ['file', 'console'],
			'level': 'ERROR'
		},
		'django_apscheduler': {
			'handlers': ['file', 'console'],
			'level': 'ERROR'
		},
		'django_apscheduler.util': {
			'handlers': ['file', 'console'],
			'level': 'ERROR'
		},
		'django_apscheduler.models': {
			'handlers': ['file', 'console'],
			'level': 'ERROR'
		},
	},
}

REST_FRAMEWORK = {
'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated', 'rest_framework.permissions.AllowAny', 'rest_framework.permissions.IsAuthenticatedOrReadOnly'],
'DEFAULT_AUTHENTICATION_CLASSES': ['rest_framework_jwt.authentication.JSONWebTokenAuthentication', 'rest_framework.authentication.SessionAuthentication', 'rest_framework.authentication.BasicAuthentication'],
'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend'],
'DEFAULT_THROTTLE_CLASSES': [
'rest_framework.throttling.AnonRateThrottle',
'rest_framework.throttling.UserRateThrottle'
],
'DEFAULT_THROTTLE_RATES': {
'anon': '100/day',
'user': '1000/second'
},
'EXCEPTION_HANDLER': 'rest_framework.views.exception_handler',
'DEFAULT_RENDERER_CLASSES': (
'rest_framework.renderers.JSONRenderer',
'rest_framework.renderers.BrowsableAPIRenderer',
'rest_framework_swagger.renderers.SwaggerUIRenderer',
'rest_framework_swagger.renderers.OpenAPIRenderer',
# 'drf_renderer_xlsx.renderers.XLSXRenderer',
),
'DEFAULT_SCHEMA_CLASS':'rest_framework.schemas.coreapi.AutoSchema'
}


JWT_AUTH = {
'JWT_AUTH_HEADER_PREFIX': 'Bearer',
'JWT_SECRET_KEY': SECRET_KEY,
'JWT_VERIFY': True,
'JWT_VERIFY_EXPIRATION': True,
'JWT_LEEWAY': 0,
'JWT_EXPIRATION_DELTA': datetime.timedelta(days=2),
'JWT_ALLOW_REFRESH': True,
'JWT_RESPONSE_PAYLOAD_HANDLER': 'api.views.jwt_response_payload_handler'
}

SIMPLE_JWT = {
'ACCESS_TOKEN_LIFETIME': datetime.timedelta(days=1),
'REFRESH_TOKEN_LIFETIME': datetime.timedelta(days=2),
'ROTATE_REFRESH_TOKENS': True
}

CORS_ORIGIN_ALLOW_ALL = True

AUTH_USER_MODEL = 'users.User'

USER_ROLES_MAIN = ('superadmin', 'developer')

REST_FLEX_FIELDS = {'EXPAND_PARAM':'expand'}

NOTIFY_MAILS = ['usermicrodevices@gmail.com']

ADMIN_PATH_PREFIX = '/api/admin'
