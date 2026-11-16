# helpdesk.KnowledgeService

Version: 1.0.0
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
| Article | createdAt, updatedAt, id, title, summary, body, topic, published, helpful, notHelpful | id |  |

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/help/articles | articles |
| GET | /api/v1/help/search/:query | search |
| GET | /api/v1/help/articles/:id | article |
| POST | /api/v1/help/articles/:id/vote | vote |
| GET | /api/v1/desk/articles | list_articles |
| GET | /api/v1/desk/articles/:id | get_article |
| POST | /api/v1/desk/articles | create_article |
| PUT | /api/v1/desk/articles/:id | update_article |
| DELETE | /api/v1/desk/articles/:id | delete_article |






## Runtime configuration

Runtime configuration is resolved from generated bootstrap constants, the runtime config store, and the secrets resolver. This service does not use a `.env.example` contract.

