from django.contrib import admin
from .models import Event, TicketType


class TicketTypeInline(admin.TabularInline):
    model = TicketType
    extra = 0


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('name', 'venue', 'start_at', 'total_capacity')
    list_filter = ('start_at',)
    search_fields = ('name', 'venue')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [TicketTypeInline]


@admin.register(TicketType)
class TicketTypeAdmin(admin.ModelAdmin):
    list_display = ('event', 'name', 'price', 'quantity_total', 'quantity_sold')
    list_filter = ('event',)
