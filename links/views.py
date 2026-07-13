import json
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from .models import Link, ClickLog
from django.shortcuts import redirect
from django.http import HttpResponseGone, HttpResponseNotFound
from django.views.decorators.cache import never_cache
from django_ratelimit.decorators import ratelimit
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.contrib.auth import authenticate, login
import re


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(login_required, name='dispatch')
class LinkCreateView(View):
    @method_decorator(ratelimit(key='ip', rate='10/m', method='POST', block=True))
    def post(self, request):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        original_url = data.get('original_url')
        if not original_url:
            return JsonResponse({'error': 'original_url is required'}, status=400)

        SHORT_CODE_PATTERN = re.compile(r'^[A-Za-z0-9_-]{1,20}$')
        custom_code = data.get('custom_code')
        expires_at_str = data.get('expires_at')

        if custom_code is not None:
            if custom_code == '':
                return JsonResponse({
                    'error': 'custom_code must not be empty if provided'
                }, status=400)

            if not SHORT_CODE_PATTERN.match(custom_code):
                return JsonResponse({
                    'error': 'Invalid custom_code. Only letters, digits, underscore and hyphen allowed, max 20 characters.'
                }, status=400)

            if Link.objects.filter(short_code=custom_code).exists():
                return JsonResponse({'error': 'Custom code already taken'}, status=400)

            short_code = custom_code
        else:
            short_code = Link.generate_unique_code()

        expires_at = None
        if expires_at_str:
            try:
                expires_at = timezone.datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
                if expires_at <= timezone.now():
                    return JsonResponse({'error': 'Expiration date must be in the future'}, status=400)
            except ValueError:
                return JsonResponse({'error': 'Invalid expires_at format. Use ISO 8601'}, status=400)

        link = Link.objects.create(
            original_url=original_url,
            short_code=short_code,
            expires_at=expires_at,
            user=request.user
        )

        short_url = request.build_absolute_uri(f'/s/{short_code}')
        return JsonResponse({
            'short_url': short_url,
            'short_code': short_code,
            'original_url': link.original_url,
            'expires_at': link.expires_at.isoformat() if link.expires_at else None,
        }, status=201)


@never_cache
def redirect_view(request, short_code):
    try:
        link = Link.objects.get(short_code=short_code, is_active=True)
    except Link.DoesNotExist:
        return HttpResponseNotFound("Link not found or deleted.")

    if link.is_expired():
        link.is_active = False
        link.save(update_fields=['is_active'])
        return HttpResponseGone("The link has expired.")

    ClickLog.objects.create(
        link=link,
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )
    link.increment_clicks()

    return redirect(link.original_url)


class LinkInfoView(View):
    @method_decorator(ratelimit(key='ip', rate='30/m', method='GET', block=True))
    def get(self, request, short_code):
        try:
            link = Link.objects.get(short_code=short_code)
        except Link.DoesNotExist:
            return JsonResponse({'error': 'Not found'}, status=404)

        # Последние 20 переходов
        recent_clicks = link.clicks.order_by('-timestamp').values('timestamp', 'ip_address', 'user_agent')[:20]
        data = {
            'original_url': link.original_url,
            'short_code': link.short_code,
            'created_at': link.created_at.isoformat(),
            'expires_at': link.expires_at.isoformat() if link.expires_at else None,
            'is_active': link.is_active,
            'click_count': link.click_count,
            'recent_clicks': list(recent_clicks),
        }
        return JsonResponse(data)


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(login_required, name='dispatch')
class LinkDeactivateView(View):
    @method_decorator(ratelimit(key='ip', rate='10/m', method='POST', block=True))
    def post(self, request, short_code):
        try:
            link = Link.objects.get(short_code=short_code)
        except Link.DoesNotExist:
            return JsonResponse({'error': 'Not found'}, status=404)

        if link.user != request.user:
            return JsonResponse({'error': 'You are not the owner'}, status=403)

        link.is_active = False
        link.save(update_fields=['is_active'])
        return JsonResponse({'status': 'deactivated', 'short_code': short_code})


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(login_required, name='dispatch')
class LinkDeleteView(View):
    @method_decorator(ratelimit(key='ip', rate='10/m', method='DELETE', block=True))
    def delete(self, request, short_code):
        try:
            link = Link.objects.get(short_code=short_code)
        except Link.DoesNotExist:
            return JsonResponse({'error': 'Not found'}, status=404)

        if link.user != request.user:
            return JsonResponse({'error': 'You are not the owner'}, status=403)

        link.delete()
        return JsonResponse({'status': 'deleted', 'short_code': short_code})


@method_decorator(csrf_exempt, name='dispatch')
class LoginView(View):
    def post(self, request):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        username = data.get('username')
        password = data.get('password')
        if not username or not password:
            return JsonResponse({'error': 'username and password required'}, status=400)

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return JsonResponse({'status': 'ok', 'user': username})
        else:
            return JsonResponse({'error': 'Invalid credentials'}, status=401)
