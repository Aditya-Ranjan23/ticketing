from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from django.db import transaction
from django.db.models import F
from django.utils.decorators import method_decorator
from django.views.generic import ListView
from django.contrib import messages

from .models import Event, TicketType
from orders.models import Order, OrderItem


# Cache event list for 60s to handle high traffic
@method_decorator(cache_page(60), name='dispatch')
class EventListView(ListView):
    model = Event
    template_name = 'events/event_list.html'
    context_object_name = 'events'
    paginate_by = 20


def event_detail(request, slug):
    """Event detail with cached availability."""
    event = get_object_or_404(Event, slug=slug)
    cache_key = f'event_availability:{event.pk}'
    ticket_types = cache.get(cache_key)
    if ticket_types is None:
        ticket_types = list(
            event.ticket_types.values('id', 'name', 'price', 'quantity_total', 'quantity_sold')
        )
        for tt in ticket_types:
            tt['quantity_available'] = max(0, tt['quantity_total'] - tt['quantity_sold'])
        cache.set(cache_key, ticket_types, 30)  # 30s cache for availability
    return render(request, 'events/event_detail.html', {
        'event': event,
        'ticket_types': ticket_types,
    })


@login_required
@require_http_methods(['GET', 'POST'])
def checkout_start(request, slug):
    """Checkout: select ticket types/quantities (GET) or create Order + OrderItems (POST)."""
    event = get_object_or_404(Event, slug=slug)
    ticket_types = list(event.ticket_types.all())

    if request.method == 'GET':
        return render(request, 'events/checkout_start.html', {
            'event': event,
            'ticket_types': ticket_types,
        })

    # POST: parse quantities and create order
    qty_prefix = 'qty_'
    requested = {}
    for key, value in request.POST.items():
        if key.startswith(qty_prefix) and value.isdigit():
            try:
                tt_id = int(key[len(qty_prefix):])
                requested[tt_id] = int(value)
            except ValueError:
                pass

    if not any(q > 0 for q in requested.values()):
        messages.error(request, 'Please select at least one ticket.')
        return render(request, 'events/checkout_start.html', {
            'event': event,
            'ticket_types': ticket_types,
        })

    try:
        with transaction.atomic():
            # Lock ticket types for this event to avoid overselling
            types_locked = {
                tt.id: tt
                for tt in TicketType.objects.filter(event=event).select_for_update()
            }
            order_total = Decimal('0')
            items_to_create = []

            for tt_id, qty in requested.items():
                if qty <= 0:
                    continue
                tt = types_locked.get(tt_id)
                if not tt or tt.event_id != event.pk:
                    continue
                available = tt.quantity_total - tt.quantity_sold
                if qty > available:
                    messages.error(
                        request,
                        f'Only {available} "{tt.name}" ticket(s) left. Please adjust quantity.',
                    )
                    return render(request, 'events/checkout_start.html', {
                        'event': event,
                        'ticket_types': ticket_types,
                    })

                unit_price = tt.price
                line_total = unit_price * qty
                order_total += line_total
                items_to_create.append((tt, qty, unit_price, line_total))

            if not items_to_create:
                messages.error(request, 'Please select at least one ticket.')
                return render(request, 'events/checkout_start.html', {
                    'event': event,
                    'ticket_types': ticket_types,
                })

            order = Order.objects.create(
                user=request.user,
                session_key=request.session.session_key or '',
                event=event,
                status=Order.STATUS_PENDING,
                total_amount=order_total,
            )
            for tt, qty, unit_price, line_total in items_to_create:
                OrderItem.objects.create(
                    order=order,
                    ticket_type=tt,
                    quantity=qty,
                    unit_price=unit_price,
                    line_total=line_total,
                )
                TicketType.objects.filter(pk=tt.pk).update(
                    quantity_sold=F('quantity_sold') + qty,
                )

        cache.delete(f'event_availability:{event.pk}')
        messages.success(request, f'Order #{order.pk} created. You can view it in My orders.')
        return redirect('order_detail', pk=order.pk)

    except Exception:
        messages.error(request, 'Something went wrong. Please try again.')
        return render(request, 'events/checkout_start.html', {
            'event': event,
            'ticket_types': ticket_types,
        })
