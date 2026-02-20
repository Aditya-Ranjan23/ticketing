"""
Load 5–8 demo events with ticket types. Run: python manage.py load_demo_events
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from events.models import Event, TicketType


DEMO_EVENTS = [
    {
        "name": "Summer Night Concert 2026",
        "slug": "summer-night-concert-2026",
        "venue": "Central Park Amphitheatre",
        "description": "An evening of live music under the stars. Featuring indie bands and acoustic sets. Bring a blanket and enjoy the best of local and national artists.",
        "days_ahead": 45,
        "ticket_types": [
            ("General Admission", 29.99, 500),
            ("VIP (front row)", 79.99, 50),
        ],
    },
    {
        "name": "Tech Summit 2026",
        "slug": "tech-summit-2026",
        "venue": "Convention Center Hall A",
        "description": "Two days of keynotes, workshops, and networking. Topics include AI, cloud, security, and product. Breakfast and lunch included.",
        "days_ahead": 30,
        "ticket_types": [
            ("Early Bird", 149.00, 200),
            ("Standard", 199.00, 400),
            ("Workshop Pass", 299.00, 100),
        ],
    },
    {
        "name": "Comedy Night Live",
        "slug": "comedy-night-live",
        "venue": "The Laugh Factory",
        "description": "Stand-up comedy night with headline acts and open mic. 18+ only. Doors open 7 PM, show at 8 PM.",
        "days_ahead": 14,
        "ticket_types": [
            ("Standard", 25.00, 300),
            ("Table for 4", 120.00, 20),
        ],
    },
    {
        "name": "Marathon City Run",
        "slug": "marathon-city-run",
        "venue": "City Downtown Start Line",
        "description": "Annual city marathon: full marathon, half marathon, and 5K. Timing chips, medal, and refreshments included. Early start for full marathon.",
        "days_ahead": 60,
        "ticket_types": [
            ("5K", 35.00, 1000),
            ("Half Marathon", 65.00, 500),
            ("Full Marathon", 95.00, 300),
        ],
    },
    {
        "name": "Jazz & Blues Festival",
        "slug": "jazz-blues-festival",
        "venue": "Riverside Festival Grounds",
        "description": "Weekend festival with multiple stages. Food trucks, craft vendors, and non-stop jazz and blues from noon till midnight.",
        "days_ahead": 90,
        "ticket_types": [
            ("Single Day", 45.00, 800),
            ("Weekend Pass", 85.00, 400),
        ],
    },
    {
        "name": "Startup Pitch Night",
        "slug": "startup-pitch-night",
        "venue": "Innovation Hub",
        "description": "Watch early-stage startups pitch to investors. Networking and light refreshments. Free for students with valid ID.",
        "days_ahead": 7,
        "ticket_types": [
            ("General", 15.00, 150),
            ("Student", 0.00, 50),
        ],
    },
    {
        "name": "Film Premiere: Midnight Drive",
        "slug": "film-premiere-midnight-drive",
        "venue": "Grand Cinema",
        "description": "Exclusive premiere screening with Q&A from the director and cast. Red carpet from 6 PM, screening at 7:30 PM.",
        "days_ahead": 21,
        "ticket_types": [
            ("Balcony", 18.00, 100),
            ("Stalls", 25.00, 200),
            ("VIP + After-party", 75.00, 30),
        ],
    },
    {
        "name": "Kids Science Fair",
        "slug": "kids-science-fair",
        "venue": "Science Museum Atrium",
        "description": "Hands-on experiments, planetarium show, and meet real scientists. Suitable for ages 5–12. Sessions at 10 AM and 2 PM.",
        "days_ahead": 10,
        "ticket_types": [
            ("Child", 12.00, 400),
            ("Adult", 15.00, 200),
        ],
    },
]


class Command(BaseCommand):
    help = "Load 5–8 demo events with ticket types (idempotent: skips existing slugs)."

    def handle(self, *args, **options):
        created = 0
        skipped = 0
        base = timezone.now().replace(hour=19, minute=0, second=0, microsecond=0)

        for i, data in enumerate(DEMO_EVENTS):
            if Event.objects.filter(slug=data["slug"]).exists():
                skipped += 1
                continue
            start = base + timedelta(days=data["days_ahead"])
            end = start + timedelta(hours=3) if "Festival" not in data["name"] and "Summit" not in data["name"] else start + timedelta(days=2)
            total_cap = sum(tt[2] for tt in data["ticket_types"])
            event = Event.objects.create(
                name=data["name"],
                slug=data["slug"],
                venue=data["venue"],
                description=data["description"],
                start_at=start,
                end_at=end,
                total_capacity=total_cap,
            )
            for name, price, qty in data["ticket_types"]:
                TicketType.objects.create(
                    event=event,
                    name=name,
                    price=price,
                    quantity_total=qty,
                )
            created += 1

        self.stdout.write(self.style.SUCCESS(f"Created {created} demo events, skipped {skipped} (already exist)."))
