import logging, json, site, time, os, re, sys
from datetime import datetime as dt, timezone as tz, timedelta

try:
	from zoneinfo import ZoneInfo
except:
	from backports.zoneinfo import ZoneInfo

from django.conf import settings
os.path.join(settings.BASE_DIR)

from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.contrib.auth.models import update_last_login
from django.utils import timezone as django_tz
from django.core.exceptions import ObjectDoesNotExist
from django.db.utils import IntegrityError
from django.db.models import F, Q, OuterRef, Subquery
from django.template import Context, Template
from django.core.mail import send_mail
from django.utils.dateparse import parse_datetime
from django.db.models.functions import Now
from django.db.models.expressions import RawSQL
from django.core.serializers import serialize
from django.forms.models import model_to_dict

from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.schemas.coreapi import SchemaGenerator

from core.models import Equipment, NotificationSource, NotificationOption, NotificationTemplate, NotificationBulkEmail

from users.models import User
from users.serializers import UserSerializer

TZRU = tz(timedelta(0, 10800))
RATIO_TEMPERATURE = 10000
RATIO_TDS = 10000
RATIO_CURRENT_STRENGTH = 40
RATIO_VOLTAGE = 10000


def logi(*args):
	msg = f'💡{sys._getframe().f_back.f_code.co_name}'
	for arg in args:
		msg += f'::{arg}'
	logging.info(msg)

def logw(*args):
	msg = f'⚠️{sys._getframe().f_back.f_code.co_name}'
	for arg in args:
		msg += f'::{arg}'
	logging.warning(msg)

def loge(err, *args):
	msg = f'❗{err.__traceback__.tb_frame.f_code.co_name}::{err}::LINE={err.__traceback__.tb_lineno}'
	for arg in args:
		msg += f'::{arg}'
	logging.error(msg)

@api_view(['GET'])
def handle_version(_):
	s = os.stat(__file__)
	return JsonResponse({'version': '{}'.format(django_tz.make_aware(dt.fromtimestamp(s.st_atime)))})

@api_view(['GET'])
def get_current_user(request):
	return JsonResponse(UserSerializer(request.user).data, safe=False)

def jwt_response_payload_handler(token, user=None, request={}, _=None):
	update_last_login(None, user)
	if request.method == 'POST':
		regid = request.POST.get('registration_id', None)
		if regid:
			pdevices = GCMDevice.objects.filter(~Q(user_id=user.id), registration_id=regid)
			for pd in pdevices:
				pd.update(user_id = user.id)
	return {'token': token, 'user': UserSerializer(user).data if user else None}

def notify(obj, source_value='', obj_description='', exclude_users=[]):
	nsrc = NotificationSource.objects.filter(value=source_value).first()
	if not nsrc:
		return
	subject = f'{obj._meta.verbose_name} [{obj_description}]'
	users_conditions = Q()
	if exclude_users:
		users_conditions &= ~Q(id__in=exclude_users)
	users = User.objects.filter(users_conditions).only('id', 'email').distinct()
	list_check_emails = []
	for user in users:
		ntf_option = NotificationOption.objects.filter(owner__id=user.id, source_id=nsrc.id).exclude().first()
		if not ntf_option:
			ntf_option = NotificationOption.objects.filter(owner__id=0, source_id=nsrc.id).first()
		if ntf_option:
			for t in ntf_option.types.all():
				if t.value == 'email':
					if not user.email or user.email == 'email@email.ru':
						continue
					try:
						template_email = NotificationTemplate.objects.get(source__id=ntf_option.source.id, notification_type__id=t.id)
					except NotificationTemplate.DoesNotExist as e:
						loge(e, self, ntf_option.source, t)
					except Exception as e:
						loge(e)
					else:
						try:
							email_message = Template(template_email.body).render(Context({'target_user':user, 'source':nsrc}))
						except Exception as e:
							loge(e)
						else:
							try:
								send_mail(subject, '', '', (user.email,), html_message=email_message)
							except Exception as e:
								loge(e)
							else:
								logi('✉️->📧 {} : {}'.format(user, user.email))
								if user.email not in list_check_emails:
									list_check_emails.append(user.email)
								else:
									prefix = '{} 📧'.format(sys._getframe().f_code.co_name)
									suffix = 'EMAIL IS DOUBLE FOR THIS NOTIFY'
									msg = '{} [{} ({}) {}]'.format(prefix, user.username, user.email, suffix)
									logw(msg)
									for email in settings.NOTIFY_MAILS:
										try:
											send_mail('DOUBLE EMAIL FOR NOTIFY', '', '', (email,), html_message=f'<html><body>{prefix} [<a href="{settings.HOST}/api/admin/users/user/?q={user.email}">{user.username} ({user.email})</a> {suffix}]</body></html>')
										except Exception as e:
											loge(e)
	######SEARCH FROM NotificationBulkEmail######
	bulk_emails = NotificationBulkEmail.objects.filter(notifications__contains=[{'sources':[nsrc.id]}])
	bulk_emails_count = bulk_emails.count()
	if bulk_emails_count:
		email_message = '<html><body><p>{}</p><p>{}</p><p>{}</p></body></html>'.format(obj_description, device.sale_point.name, device.name)
		prefix = '{} 📧'.format(sys._getframe().f_code.co_name)
		suffix = ''
		for bulk_email in bulk_emails:
			for email_adr in bulk_email.emails.split(';'):
				if email_adr not in list_check_emails:
					list_check_emails.append(email_adr)
					try:
						send_mail(subject, '', '', (email_adr,), html_message=email_message)
					except Exception as e:
						loge(e, 'NotificationBulkEmail')
					else:
						logi('(NotificationBulkEmail) ✉️->📧 {} :: {} :: [{}...|{}|{}]'.format(user, user.email, obj_description[:20]))
				else:
					suffix = ' EMAIL IS DOUBLE FOR THIS NOTIFY'
					msg = '{} [{} ({}){}]'.format(prefix, user.username, email_adr, suffix)
					logw(msg)
					for email in settings.NOTIFY_MAILS:
						send_mail('DOUBLE EMAIL FOR NOTIFY', '', '', (email,), html_message='<html><body>{} {}{}</body></html>'.format(prefix, email_adr, suffix))


@csrf_exempt
def index(request):
	request_body = ''
	if request.method != 'POST':
		logi(request, request.headers, request.body.decode('utf-8'), request._stream.read().decode('utf-8'))
	else:
		try:
			d = json.loads(request.body)
		except json.decoder.JSONDecodeError as e:
			loge(e)
			return HttpResponse('0')
		except Exception as e:
			loge(e)
			return HttpResponse('0')
		logi(d)
	return HttpResponse('1')
