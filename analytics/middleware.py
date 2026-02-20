"""
Middleware to log every page/action for each visitor.
Tracks: listing view, event detail, checkout start, order view, etc.
Respects rate limiting so we don't write a log on every single request (e.g. every 2s per session).
"""
import logging
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


def _get_client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '') or None


def _action_from_path(path, method):
    """Map URL path to a simple action label for analytics."""
    path = (path or '').strip('/')
    if not path:
        return 'listing_view'
    parts = path.split('/')
    if 'checkout' in path:
        return 'checkout_start'
    if 'orders' in path and len(parts) >= 2 and parts[1].isdigit():
        return 'order_view'
    if 'orders' in path:
        return 'order_list'
    if 'event' in path and len(parts) >= 2:
        return 'event_detail'
    if method != 'GET':
        return 'form_submit'
    return 'page_view'


def _resource_from_path(path):
    """Extract resource type and id from path (e.g. event slug, order pk)."""
    path = (path or '').strip('/')
    parts = path.split('/')
    if 'event' in path:
        try:
            idx = parts.index('event')
            if idx + 1 < len(parts):
                return 'event', parts[idx + 1]
        except ValueError:
            pass
    if 'orders' in path:
        try:
            idx = parts.index('orders')
            if idx + 1 < len(parts) and parts[idx + 1].isdigit():
                return 'order', parts[idx + 1]
        except ValueError:
            pass
    return '', ''


def _log_activity_sync(request, action, path, resource_type, resource_id):
    """Write one log row (sync)."""
    from .models import UserActivityLog

    UserActivityLog.objects.create(
        session_key=request.session.session_key or '',
        user=request.user if request.user.is_authenticated else None,
        action=action,
        path=path,
        method=request.method,
        resource_type=resource_type,
        resource_id=resource_id,
        referer=request.META.get('HTTP_REFERER', '')[:1000],
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
        ip_address=_get_client_ip(request),
    )


def _log_activity_async(request, action, path, resource_type, resource_id):
    """Queue log to Celery (async) to avoid blocking under 90k traffic."""
    try:
        from .tasks import log_user_activity_task
        if log_user_activity_task is not None:
            log_user_activity_task.delay(
                session_key=request.session.session_key or '',
                user_id=request.user.id if request.user.is_authenticated else None,
                action=action,
                path=path,
                method=request.method,
                resource_type=resource_type,
                resource_id=resource_id,
                referer=request.META.get('HTTP_REFERER', '')[:1000],
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                ip_address=_get_client_ip(request),
            )
        else:
            _log_activity_sync(request, action, path, resource_type, resource_id)
    except Exception as e:
        logger.warning("Async activity log failed, falling back to sync: %s", e)
        _log_activity_sync(request, action, path, resource_type, resource_id)


class UserActivityMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        # Only log successful GET/HEAD or meaningful POST (e.g. checkout)
        if response.status_code != 200:
            return response
        if request.method not in ('GET', 'HEAD', 'POST'):
            return response

        path = request.path
        action = _action_from_path(path, request.method)
        resource_type, resource_id = _resource_from_path(path)

        # Skip static/admin to reduce noise
        if path.startswith(('/static/', '/admin/', '/favicon', '/__debug__')):
            return response

        # Rate limit: one log per session per N seconds
        rate_key = f"activity_log_rate:{request.session.session_key or request.META.get('REMOTE_ADDR', '')}"
        if cache.get(rate_key):
            return response
        cache.set(rate_key, 1, getattr(settings, 'ANALYTICS_RATE_LIMIT_SECONDS', 2))

        if getattr(settings, 'ANALYTICS_LOG_ASYNC', False):
            _log_activity_async(request, action, path, resource_type, resource_id)
        else:
            _log_activity_sync(request, action, path, resource_type, resource_id)

        return response
