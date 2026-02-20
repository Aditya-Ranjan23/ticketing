# Advanced Ticketing Website

A Django-based ticketing system built to handle **high traffic** (e.g. ~90k concurrent users) with **user activity logging** so you can see what each visitor did (listing view, event detail, checkout start, order view).

## Features

- **Scale-ready**: Redis cache, optional Celery for async work, connection pooling, cached event list and availability.
- **User activity logs**: Every visitor is tracked by session (and user if logged in). You see:
  - **Last action**: e.g. "checkout_start", "event_detail", "listing_view", "order_view".
  - **Full journey**: time-ordered list of pages/actions per session or user.
- **Admin**: Under **User activity logs** you can filter by session, user, action, or time and see exactly what each person did.

## Quick start

```bash
cd ticketing
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
# Optional: install Redis and set REDIS_URL for caching
python manage.py migrate
# If migrate fails with "ENGINE" or "dummy" error, use: set DJANGO_SETTINGS_MODULE=ticketing.settings.base
python manage.py createsuperuser
python manage.py runserver
```

- **Events**: http://127.0.0.1:8000/
- **Admin (activity logs)**: http://127.0.0.1:8000/admin/ → **User activity logs**

## How activity logging works

1. **Middleware** (`analytics.middleware.UserActivityMiddleware`) runs on each request and logs:
   - `listing_view` – homepage / event list
   - `event_detail` – viewing an event page
   - `checkout_start` – opened checkout
   - `order_view` / `order_list` – viewing order(s)
   - `page_view` – other pages

2. Each log stores: **session_key**, **user** (if logged in), **action**, **path**, **resource_type** (e.g. event), **resource_id** (e.g. event slug), **referer**, **user_agent**, **ip_address**, **created_at**.

3. **Rate limiting**: One log per session every 2 seconds (configurable via `ANALYTICS_RATE_LIMIT_SECONDS`) to avoid write overload.

4. **Async at scale**: Set `ANALYTICS_LOG_ASYNC=True` and run Celery; logs are written via a Celery task so the request isn’t blocked by DB writes.

## Getting “last thing this person did” and full journey

- **By session** (anonymous): In admin, filter **User activity logs** by **Session key** (you get session_key from cookies or your auth/session store). Sort by **Created at** descending → first row is last action; full list is the journey.
- **By user**: Filter by **User**. Same ordering gives last action and full journey.
- **Programmatic**:  
  `UserActivityLog.objects.filter(session_key=...).order_by('-created_at')`  
  or  
  `UserActivityLog.objects.filter(user=user).order_by('-created_at')`  
  First record = last thing they did; full queryset = full journey.

## Handling ~90k concurrent users

| Layer | Purpose |
|-------|--------|
| **Redis cache** | Event list (e.g. 60s), event availability (e.g. 30s), rate limit for activity logs. Set `REDIS_URL`. |
| **django-redis** | Recommended for Redis cache and connection pooling. |
| **PostgreSQL** | Use in production (not SQLite). Set `DB_ENGINE`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`. |
| **CONN_MAX_AGE** | Already set (e.g. 60s) to reuse DB connections. |
| **Celery + Redis** | Set `ANALYTICS_LOG_ASYNC=True` and run Celery worker; activity logs are written asynchronously. Run `celery -A ticketing worker -l info`. |
| **Load balancer** | Run multiple Django instances behind a load balancer. |
| **CDN** | Serve static/media from a CDN. |
| **DB replicas** | For read-heavy traffic, use read replicas and Django DB router for reads. |

## Environment variables (production)

```env
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DJANGO_SECRET_KEY=your-secret-key

# PostgreSQL
DB_ENGINE=django.db.backends.postgresql
DB_NAME=ticketing
DB_USER=...
DB_PASSWORD=...
DB_HOST=...
DB_PORT=5432

# Redis (cache + optional Celery broker)
REDIS_URL=redis://127.0.0.1:6379/0
CELERY_BROKER_URL=redis://127.0.0.1:6379/1

# Async activity logging (recommended at 90k traffic)
ANALYTICS_LOG_ASYNC=True
CELERY_ALWAYS_EAGER=False
```

## Project structure

```
ticketing/
├── manage.py
├── requirements.txt
├── README.md
├── ticketing/           # project config
│   ├── settings/
│   │   └── base.py      # Redis, Celery, analytics settings
│   ├── urls.py
│   ├── celery.py
│   └── ...
├── events/              # events + ticket types
├── orders/              # orders + order items
├── analytics/           # UserActivityLog + middleware + Celery task
└── templates/
```

You can extend **events** and **orders** with payment, inventory (e.g. row/seat), and emails; the activity logging and scaling patterns stay the same.
