# realestate.ViewingService

Version: 2.0.0
## Quick start

```bash
# Install dependencies
# See scripts/install.sh

# Run service (port 8002)
# See scripts/dev.sh
```

## Entities

| Entity | Fields | Primary key | Description |
|--------|--------|-------------|-------------|
| Viewing | createdAt, updatedAt, id, startsAt, endsAt, listingTitle, buyerName, status, agentName, note, listingId, buyerEmail, agentEmail, reminderSent | id |  |

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/viewings/mine | mine |
| POST | /api/v1/viewings/request | requestViewing |
| POST | /api/v1/viewings/cancel/:id | cancel |
| GET | /api/v1/agent/viewings/viewings | list_viewings |
| GET | /api/v1/agent/viewings/summary | summary |
| GET | /api/v1/agent/viewings/calendar | calendar |
| POST | /api/v1/agent/viewings/confirm/:id | confirm |
| POST | /api/v1/agent/viewings/completed/:id | completed |
| POST | /api/v1/agent/viewings/no-show/:id | noShow |






## Runtime configuration

Runtime configuration is resolved from generated bootstrap constants, the runtime config store, and the secrets resolver. This service does not use a `.env.example` contract.

