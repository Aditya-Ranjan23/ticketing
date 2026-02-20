from django.contrib import admin
from django.contrib.auth import logout
from django.conf import settings
from django.shortcuts import redirect
from django.urls import path, include

from . import views as auth_views


def logout_view(request):
    """Log out and redirect; allows GET so nav 'Logout' link works."""
    logout(request)
    return redirect(getattr(settings, 'LOGOUT_REDIRECT_URL', '/'))


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('events.urls')),
    path('orders/', include('orders.urls')),
    path('accounts/logout/', logout_view, name='logout'),
    path('accounts/signup/', auth_views.signup_view, name='signup'),
    path('accounts/', include('django.contrib.auth.urls')),
]
