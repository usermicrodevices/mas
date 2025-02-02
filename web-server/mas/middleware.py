from django.utils import timezone


class TimezoneMiddleware:
	def __init__(self, get_response):
		self.get_response = get_response

	def __call__(self, request):
		tzname = request.session.get('django_timezone')
		#if not tzname and hasattr(request, 'user') and not request.user.is_anonymous:
			#tzname = request.user.tz
		if tzname:
			timezone.activate(tzname)
		else:
			timezone.deactivate()
		return self.get_response(request)
