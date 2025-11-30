# Database Migration Guide

## Initial Setup

After setting up your database, create the initial migration:

```bash
cd backend
alembic revision --autogenerate -m "Initial schema: users, strategies, ai_reports, payment_events, daily_picks"
alembic upgrade head
```

## Models Created

All models are defined in `app/db/models.py`:

1. **User** - User accounts with Google OAuth and Pro subscription
2. **Strategy** - Option strategies with JSONB legs
3. **AIReport** - AI-generated analysis reports
4. **PaymentEvent** - Lemon Squeezy webhook audit trail
5. **DailyPick** - Daily AI strategy picks (Cold Start solution)

## Key Features

- All timestamps are stored in UTC
- UUID primary keys for all tables
- JSONB for flexible data storage (strategy legs, payment payloads)
- Proper indexes on foreign keys and unique fields

