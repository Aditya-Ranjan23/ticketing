from django.db import models
from django.conf import settings


class UserActivityLog(models.Model):
    """
    Log of what each visitor did on the site: page views, checkout start, listing view, etc.
    Query by session_key or user to see "last thing this person did" and full journey.
    """
    # Who: anonymous by session, or user if logged in
    session_key = models.CharField(max_length=40, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activity_logs',
        db_index=True,
    )

    # What happened
    action = models.CharField(max_length=50, db_index=True)
    path = models.CharField(max_length=500)
    method = models.CharField(max_length=10, default='GET')
    # Optional: event id, order id, etc. for funnel analysis
    resource_type = models.CharField(max_length=50, blank=True, db_index=True)
    resource_id = models.CharField(max_length=100, blank=True, db_index=True)

    # Request metadata
    referer = models.URLField(max_length=1000, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['session_key', '-created_at']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['action', '-created_at']),
        ]
        verbose_name = 'User activity log'
        verbose_name_plural = 'User activity logs'

    def __str__(self):
        who = self.user_id or self.session_key[:8]
        return f"{who} | {self.action} | {self.path} @ {self.created_at}"
