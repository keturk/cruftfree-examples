# cityservices.RequestService

Version: 2.0.0
## Quick start

```bash
# Install dependencies
# See scripts/install.sh

# Run service (port 8003)
# See scripts/dev.sh
```

## Entities

| Entity | Fields | Primary key | Description |
|--------|--------|-------------|-------------|
| ServiceRequest | createdAt, updatedAt, id, requestNumber, title, description, category, priority, status, address, latitude, longitude, location, districtId, districtName, reporterPhone | id |  |
| RequestUpdate | createdAt, updatedAt, id, requestId, status, note | id | What happened to a request, in order. The table refuses every change and delete. |

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/v1/reports | report |
| GET | /api/v1/reports/track/:requestNumber | track |
| GET | /api/v1/reports/nearby | nearby |
| GET | /api/v1/queue/requests/service_requests | list_service_requests |
| GET | /api/v1/queue/requests/summary | summary |
| GET | /api/v1/queue/requests/map | pins |
| GET | /api/v1/queue/requests/:id | request |
| GET | /api/v1/queue/requests/:id/history | history |
| POST | /api/v1/queue/requests/:id/assign | assign |
| POST | /api/v1/queue/requests/:id/start | start |
| POST | /api/v1/queue/requests/:id/resolve | resolve |
| POST | /api/v1/queue/requests/:id/close | close |
| POST | /api/v1/queue/requests/:id/priority | setPriority |

## Events

| Topic | Events |
|-------|--------|
| RequestEvents | RequestStatusChanged |





## Runtime configuration

Runtime configuration is resolved from generated bootstrap constants, the runtime config store, and the secrets resolver. This service does not use a `.env.example` contract.

