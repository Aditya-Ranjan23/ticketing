from django.contrib import admin
from .models import UserActivityLog


@admin.register(UserActivityLog)
class UserActivityLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_or_session', 'action', 'path_short', 'resource', 'created_at')
    list_filter = ('action', 'resource_type', 'created_at')
    search_fields = ('session_key', 'path', 'resource_id', 'user__email')
    readonly_fields = (
        'session_key', 'user', 'action', 'path', 'method',
        'resource_type', 'resource_id', 'referer', 'user_agent', 'ip_address', 'created_at',
    )
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)

    def user_or_session(self, obj):
        if obj.user_id:
            return str(obj.user)
        return f"Session {obj.session_key[:16]}..." if obj.session_key else "-"
    user_or_session.short_description = 'User / Session'

    def path_short(self, obj):
        return (obj.path[:60] + '...') if len(obj.path) > 60 else obj.path
    path_short.short_description = 'Path'

    def resource(self, obj):
        if obj.resource_type and obj.resource_id:
            return f"{obj.resource_type}:{obj.resource_id}"
        return "-"
    resource.short_description = 'Resource'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
