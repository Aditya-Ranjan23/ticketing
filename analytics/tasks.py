"""Celery task for async user activity logging (used at high scale)."""
from django.conf import settings

try:
    from celery import shared_task
except ImportError:
    shared_task = None


def _create_log(session_key, user_id, action, path, method, resource_type, resource_id, referer, user_agent, ip_address):
    from .models import UserActivityLog
    UserActivityLog.objects.create(
        session_key=session_key or '',
        user_id=user_id,
        action=action,
        path=path,
        method=method,
        resource_type=resource_type,
        resource_id=resource_id,
        referer=referer,
        user_agent=user_agent,
        ip_address=ip_address,
    )


if shared_task is not None:
    @shared_task(name='analytics.log_user_activity')
    def log_user_activity_task(
        session_key,
        user_id,
        action,
        path,
        method='GET',
        resource_type='',
        resource_id='',
        referer='',
        user_agent='',
        ip_address=None,
    ):
        _create_log(
            session_key=session_key,
            user_id=user_id,
            action=action,
            path=path,
            method=method,
            resource_type=resource_type,
            resource_id=resource_id,
            referer=referer,
            user_agent=user_agent,
            ip_address=ip_address,
        )
else:
    log_user_activity_task = None
