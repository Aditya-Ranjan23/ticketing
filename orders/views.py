from decimal import Decimal

from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST, require_http_methods
from django.db import transaction
from django.db.models import F
from django.contrib import messages
from django.core.cache import cache

from .models import Order, OrderItem


def _can_manage_order(request, order):
    """True if the request user/session is allowed to view or cancel this order."""
    if request.user.is_authenticated:
        return order.user_id == request.user.id
    return bool(order.session_key and order.session_key == request.session.session_key)


def order_list(request):
    """List orders in two sections: Cart (pending) and Cancelled."""
    if request.user.is_authenticated:
        base = Order.objects.filter(user=request.user).select_related('event')
    else:
        base = Order.objects.filter(session_key=request.session.session_key).select_related('event')
    base = base.order_by('-created_at')[:50]
    cart_orders = [o for o in base if o.status == Order.STATUS_PENDING]
    paid_orders = [o for o in base if o.status == Order.STATUS_PAID]
    cancelled_orders = [o for o in base if o.status == Order.STATUS_CANCELLED]
    return render(request, 'orders/order_list.html', {
        'cart_orders': cart_orders,
        'paid_orders': paid_orders,
        'cancelled_orders': cancelled_orders,
    })


def order_detail(request, pk):
    """Order detail - track as 'order_view' in analytics."""
    order = get_object_or_404(Order, pk=pk)
    if not _can_manage_order(request, order):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden()
    return render(request, 'orders/order_detail.html', {'order': order})


@require_POST
def order_cancel(request, pk):
    """Cancel (remove) a pending order and release ticket inventory."""
    order = get_object_or_404(Order, pk=pk)
    if not _can_manage_order(request, order):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden()
    if order.status != Order.STATUS_PENDING:
        messages.error(request, 'Only pending orders can be removed.')
        return redirect('order_list')

    try:
        with transaction.atomic():
            order.status = Order.STATUS_CANCELLED
            order.save(update_fields=['status', 'updated_at'])
            from events.models import TicketType
            for item in order.items.all():
                TicketType.objects.filter(pk=item.ticket_type_id).update(
                    quantity_sold=F('quantity_sold') - item.quantity
                )
        cache.delete(f'event_availability:{order.event_id}')
        messages.success(request, f'Order #{order.pk} has been removed.')
    except Exception:
        messages.error(request, 'Could not remove order. Please try again.')
    return redirect('order_list')


@require_http_methods(['GET', 'POST'])
def order_edit(request, pk):
    """Edit a pending order: change quantities per ticket type (same event)."""
    order = get_object_or_404(Order, pk=pk)
    if not _can_manage_order(request, order):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden()
    if order.status != Order.STATUS_PENDING:
        messages.error(request, 'Only pending orders can be edited.')
        return redirect('order_list')

    event = order.event
    ticket_types = list(event.ticket_types.all())
    current_qty = {item.ticket_type_id: item.quantity for item in order.items.all()}

    # Add editable max (available + what's in this order) and current qty per ticket type
    for tt in ticket_types:
        tt.current_qty = current_qty.get(tt.id, 0)
        tt.max_editable = tt.quantity_available + tt.current_qty

    if request.method == 'GET':
        return render(request, 'orders/order_edit.html', {
            'order': order,
            'event': event,
            'ticket_types': ticket_types,
        })

    # POST: apply new quantities
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
        messages.error(request, 'Select at least one ticket.')
        return redirect('order_edit', pk=order.pk)

    try:
        with transaction.atomic():
            from events.models import TicketType
            types_locked = {
                tt.id: tt
                for tt in TicketType.objects.filter(event=event).select_for_update()
            }
            # Available after releasing this order's tickets = current available + what this order holds
            order_total = Decimal('0')
            items_to_create = []

            for tt_id, qty in requested.items():
                if qty <= 0:
                    continue
                tt = types_locked.get(tt_id)
                if not tt or tt.event_id != event.pk:
                    continue
                in_this_order = current_qty.get(tt_id, 0)
                available = (tt.quantity_total - tt.quantity_sold) + in_this_order
                if qty > available:
                    messages.error(
                        request,
                        f'Only {available} "{tt.name}" ticket(s) available. Please adjust.',
                    )
                    return redirect('order_edit', pk=order.pk)
                unit_price = tt.price
                line_total = unit_price * qty
                order_total += line_total
                items_to_create.append((tt, qty, unit_price, line_total))

            if not items_to_create:
                for item in order.items.all():
                    TicketType.objects.filter(pk=item.ticket_type_id).update(
                        quantity_sold=F('quantity_sold') - item.quantity
                    )
                order.items.all().delete()
                order.total_amount = Decimal('0')
                order.save(update_fields=['total_amount', 'updated_at'])
                cache.delete(f'event_availability:{event.pk}')
                messages.success(request, 'Order updated. You removed all tickets.')
                return redirect('order_detail', pk=order.pk)

            # Release current order's inventory, then apply new
            for item in order.items.all():
                TicketType.objects.filter(pk=item.ticket_type_id).update(
                    quantity_sold=F('quantity_sold') - item.quantity
                )
            order.items.all().delete()

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
            order.total_amount = order_total
            order.save(update_fields=['total_amount', 'updated_at'])

        cache.delete(f'event_availability:{event.pk}')
        messages.success(request, 'Order updated.')
        return redirect('order_detail', pk=order.pk)
    except Exception:
        messages.error(request, 'Could not update order. Please try again.')
        return redirect('order_edit', pk=order.pk)
