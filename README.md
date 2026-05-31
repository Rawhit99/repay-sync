# RepaySync

Centralized backend for field and calling collection teams to log and access customer interaction history in one system.

## Overview

RepaySync solves siloed collections work by providing:

- A single interaction history per customer (who contacted, when, what was discussed)
- Field-team hierarchy enforcement (officers see assigned customers; managers inherit subtree access)
- Flat access for the calling team (any agent, any customer)
- Latest disposition visible on the customer list
- Bulk user onboarding with auto-generated credentials
- Bulk interaction import for historical data migration
- Audit logging for authenticated actions

## Tech Stack

- **Backend:** Django 5 + Django REST Framework
- **Database:** PostgreSQL 16
- **Authentication:** JWT (djangorestframework-simplejwt)
- **Containerization:** Docker Compose

## Quick Start

### Prerequisites

- Python 3.12+
- Docker & Docker Compose (for PostgreSQL)
- Git

### 1. Clone and configure

```bash
git clone <repository-url>
cd repay-sync
cp .env.example .env
```

### 2. Start PostgreSQL

```bash
docker compose up -d db
```

Wait until the database is healthy (`docker compose ps`).

### 3. Install dependencies

**Windows (PowerShell):**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**macOS / Linux:**

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Migrate and seed demo data

```bash
python manage.py migrate
python manage.py seed_demo
```

### 5. Run the server

```bash
python manage.py runserver
```

API base URL: `http://localhost:8000/api/v1/`

OpenAPI schema: `http://localhost:8000/api/schema/`  
Swagger UI: `http://localhost:8000/api/docs/`

### Run everything with Docker

```bash
cp .env.example .env
docker compose up --build
```

In another terminal:

```bash
docker compose exec web python manage.py migrate
docker compose exec web python manage.py seed_demo
```

## Demo Credentials

After running `seed_demo`, use password `demo123456`:

| Email | Role |
|-------|------|
| `senior@example.com` | Senior Manager (Field) |
| `manager1@example.com` | Manager (Field) |
| `officer1@example.com` | Collection Officer (Field) |
| `agent1@example.com` | Calling Agent |

## API Overview

### Authentication

```bash
# Obtain JWT
curl -X POST http://localhost:8000/api/v1/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"email": "officer1@example.com", "password": "demo123456"}'

# Refresh token
curl -X POST http://localhost:8000/api/v1/auth/token/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh": "<refresh_token>"}'
```

Use the access token: `Authorization: Bearer <access_token>`

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/token/` | Obtain JWT |
| POST | `/auth/token/refresh/` | Refresh JWT |
| GET | `/users/me/` | Current user profile |
| POST | `/users/bulk-upload/` | Bulk user onboarding (CSV) |
| GET | `/customers/` | Customer list with latest disposition |
| GET | `/customers/{id}/` | Customer detail |
| POST | `/customers/` | Create customer |
| GET | `/customers/{id}/interactions/` | Interaction history |
| POST | `/interactions/` | Log interaction |
| GET | `/interactions/{id}/` | Interaction detail |
| PATCH | `/interactions/{id}/` | Update interaction |
| POST | `/interactions/bulk-upload/` | Bulk interaction import (CSV) |
| GET | `/audit-logs/` | Audit trail (managers / superuser) |

### Example: List customers

```bash
curl http://localhost:8000/api/v1/customers/ \
  -H "Authorization: Bearer <access_token>"
```

Response includes `latest_disposition` and `latest_contacted_at` per customer.

### Example: Log an interaction

```bash
curl -X POST http://localhost:8000/api/v1/interactions/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "customer": "<customer_uuid>",
    "disposition": "PROMISE_TO_PAY",
    "notes": "Customer will pay by end of week.",
    "contacted_at": "2026-05-30T10:00:00Z"
  }'
```

### Bulk uploads

Sample CSV files are in [`samples/`](samples/). Run `seed_demo` first, then use these files (they reference demo customers and managers).

**Users** (`POST /users/bulk-upload/`, multipart field `file`, managers/senior managers only):

```csv
email,full_name,team,role,manager_email
officer3@example.com,Carol Officer,FIELD,COLLECTION_OFFICER,manager1@example.com
agent2@example.com,Brian Agent,CALLING,CALLING_AGENT,
```

Returns generated passwords **once** in the response (not stored in plaintext).

**Interactions** (`POST /interactions/bulk-upload/`):

```csv
customer_external_id,user_email,disposition,notes,contacted_at
CUST-001,officer1@example.com,CONTACTED,Field visit,2026-05-29T11:00:00Z
CUST-002,officer1@example.com,REFUSED,Customer refused,2026-05-28T09:45:00Z
```

Supports partial success: valid rows are committed; invalid rows are reported with row numbers.

## Error responses

All API errors return a consistent envelope:

```json
{
  "error": {
    "code": "CUSTOMER_ACCESS_DENIED",
    "message": "You do not have access to this customer.",
    "details": {"customer_id": "..."}
  }
}
```

Common codes: `VALIDATION_ERROR`, `PERMISSION_DENIED`, `NOT_FOUND`, `CONFLICT`, `INVALID_CSV`, `INVALID_FILE`, `INVALID_DISPOSITION`.

## Running Tests

```bash
python manage.py test tests
```

Tests run against an in-memory SQLite database (no Docker required). Production and development use PostgreSQL.

## Design Decisions

### App structure

Four domain apps under `apps/`, plus shared utilities in `apps/common/`:

- **accounts** — custom User model, JWT auth, bulk user onboarding
- **customers** — Customer and CustomerAssignment
- **interactions** — Interaction records and disposition enum
- **audit** — AuditLog and request logging mixin
- **common** — CSV parsing, bulk upload base view, shared result types

This keeps boundaries clear and avoids a monolithic `core` app.

### User model and hierarchy

- `email` is the login identifier (`USERNAME_FIELD`)
- `team`: `FIELD` or `CALLING`
- `role`: `COLLECTION_OFFICER`, `MANAGER`, `SENIOR_MANAGER`, `CALLING_AGENT`
- Field hierarchy via self-referential `reports_to` FK

**Why `reports_to` instead of a closure table?** The brief describes a shallow hierarchy (officer → manager → senior manager). A self-FK with BFS subtree traversal is simple, testable, and sufficient. A closure table would scale better for deep trees but adds complexity not required here.

### Customer assignments

`CustomerAssignment` is a separate table rather than a direct FK on `Customer` so reassignment history can be added later. A `UniqueConstraint` on `customer` enforces one active assignment per customer for MVP.

### Permissions

Central access logic lives in `apps/customers/services/access.py`:

- **Calling team:** unrestricted customer access
- **Collection officer:** customers assigned to them
- **Managers / senior managers:** customers assigned to any collection officer in their reporting subtree (single-query BFS over an in-memory adjacency map)

DRF permission classes delegate to this service so list, detail, create, and bulk import share one rule set. `user_can_access_customer()` uses an `.exists()` lookup — never materializes the full accessible ID set into Python.

**Interaction updates:** any user with customer access may update interactions for that customer (field officers on assigned customers, managers on subtree, calling agents on all). Aligns with the brief: officers update records for customers assigned to them.

### Caching strategy

- **Request-scoped:** `CustomerAccessService` and `ReportingTree` are reused within a single HTTP request via `RequestContextMiddleware` + context variables.
- **Process-level:** `ReportingTree` is cached globally until hierarchy changes.
- **Invalidation:** Django signals on `User` save/delete call `invalidate_reporting_tree_cache()` so bulk onboarding and admin edits never serve stale hierarchy.

### Performance choices

- Customer list latest disposition via `Subquery` annotation (no N+1)
- Hierarchy: one DB query per cache generation, BFS traversal in memory
- Bulk interaction import batch-fetches customers/users and uses `bulk_create`
- Bulk user import preloads existing emails in one query to avoid per-row existence checks

### Latest disposition

Customer list uses a `Subquery` annotation (not N+1 per-row queries):

```python
Interaction.objects.filter(customer=OuterRef("pk")).order_by("-contacted_at", "-created_at")
```

Tie-breaker on `created_at` ensures deterministic results when `contacted_at` is identical.

### Bulk upload trade-offs

- **Users:** rows processed in dependency order (managers before officers). Passwords returned once in API response — not emailed (out of scope).
- **Interactions:** row-level validation with partial success — valid rows committed, failures collected. Safer for migration than all-or-nothing when source data is messy.

### Audit logging

`AuditLogMixin` on viewsets logs authenticated actions after successful responses. Bulk uploads log even on partial failure. Login is audited via a custom token view. Sensitive fields (passwords, tokens) are redacted from metadata.

Audit log read access is restricted to field managers and superusers.

### Authentication

JWT via `djangorestframework-simplejwt` with a custom serializer using `email` instead of username.

## Assumptions

| Topic | Assumption |
|-------|------------|
| Field roles | Three levels: collection officer, manager, senior manager |
| Hierarchy | Self-referential `reports_to`; managers inherit subtree access |
| Calling team | Single role `CALLING_AGENT`; no customer assignment |
| Customer identity | Unique `external_id` business key |
| Disposition | Fixed enum per interaction; latest = most recent `contacted_at` |
| Bulk credentials | Returned once in API response, not persisted in plaintext |
| Customer creation | Calling team and field managers may create customers |
| Bulk user upload | Field managers and superusers only |

## Future Improvements

- WebSocket notifications for real-time interaction updates
- Email/SMS delivery of bulk-upload credentials
- Assignment history and reassignment workflow
- Closure table or materialized path for deeper hierarchies
- Celery-backed async bulk processing for very large CSV files
