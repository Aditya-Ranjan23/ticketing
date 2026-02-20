from django.db import models
from django.conf import settings


class Event(models.Model):
    """A ticketed event (concert, game, etc.)."""
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    venue = models.CharField(max_length=255)
    start_at = models.DateTimeField()
    end_at = models.DateTimeField(null=True, blank=True)
    total_capacity = models.PositiveIntegerField(default=0)  # total sellable tickets
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_at']

    def __str__(self):
        return self.name


class TicketType(models.Model):
    """Ticket tier for an event (e.g. VIP, General)."""
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='ticket_types')
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity_total = models.PositiveIntegerField()
    quantity_sold = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.event.name} - {self.name}"

    @property
    def quantity_available(self):
        return max(0, self.quantity_total - self.quantity_sold)
