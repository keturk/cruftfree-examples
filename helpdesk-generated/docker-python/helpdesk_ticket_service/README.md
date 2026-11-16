# helpdesk.TicketService

Version: 1.0.0
## Quick start

```bash
# Install dependencies
# See scripts/install.sh

# Run service (port 8001)
# See scripts/dev.sh
```

## Entities

| Entity | Fields | Primary key | Description |
|--------|--------|-------------|-------------|
| Ticket | createdAt, updatedAt, id, number, subject, topic, priority, status, customerId, customerName, customerEmail, assigneeId, assigneeName, respondBy, firstRepliedAt, resolvedAt, breached, satisfaction | id |  |
| TicketMessage | createdAt, updatedAt, id, ticketId, authorName, fromCustomer, internal, body | id | One thing said on a ticket. Never changed afterwards: what was said stays said. |
| ResponsePolicy | createdAt, updatedAt, id, priority, minutes | id | How long each priority may wait for a first answer. |
| SavedReply | createdAt, updatedAt, id, title, body | id | An answer agents send often, editable in the Console. |

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/tickets | mine |
| GET | /api/v1/tickets/:id | thread |
| POST | /api/v1/tickets | openTicket |
| POST | /api/v1/tickets/reply | addReply |
| POST | /api/v1/tickets/:id/rate | rate |
| GET | /api/v1/agent/tickets | list_tickets |
| GET | /api/v1/agent/saved_replies | list_saved_replies |
| GET | /api/v1/agent/saved_replies/:id | get_saved_reply |
| POST | /api/v1/agent/saved_replies | create_saved_reply |
| PUT | /api/v1/agent/saved_replies/:id | update_saved_reply |
| DELETE | /api/v1/agent/saved_replies/:id | delete_saved_reply |
| GET | /api/v1/agent/reply-choices | replyChoices |
| GET | /api/v1/agent/queue | queue |
| GET | /api/v1/agent/mine | assignedToMe |
| GET | /api/v1/agent/threads/:id | threadView |
| POST | /api/v1/agent/threads/:id/claim | claim |
| POST | /api/v1/agent/reply | reply |
| POST | /api/v1/agent/note | note |
| POST | /api/v1/agent/threads/:id/move | move |
| GET | /api/v1/agent/summary | summary |
| GET | /api/v1/agent/volume | volume |

## Events

| Topic | Events |
|-------|--------|
| TicketEvents | TicketOpened, AgentReplied, TicketResolved, ResponseLate |





## Runtime configuration

Runtime configuration is resolved from generated bootstrap constants, the runtime config store, and the secrets resolver. This service does not use a `.env.example` contract.

