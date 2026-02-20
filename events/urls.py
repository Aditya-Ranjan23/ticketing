from django.urls import path
from . import views

urlpatterns = [
    path('', views.EventListView.as_view(), name='event_list'),
    path('event/<slug:slug>/', views.event_detail, name='event_detail'),
    path('event/<slug:slug>/checkout/', views.checkout_start, name='checkout_start'),
]
