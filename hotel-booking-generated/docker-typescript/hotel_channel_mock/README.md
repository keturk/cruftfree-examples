# hotel.ChannelMock

Version: 1.0.0
## Quick start

```bash
# Install dependencies
# See scripts/install.sh

# Run service (port 8092)
# See scripts/dev.sh
```

## Entities

| Entity | Fields | Primary key | Description |
|--------|--------|-------------|-------------|
| PublishedNight | createdAt, updatedAt, id, roomType, night, left, nightlyRate, receivedAt | id | What the travel sites currently believe about one room type on one night. |
| ApiKey | createdAt, updatedAt, id, keyHash, ownerId, scopes, isActive, expiresAt, lastUsedAt | id | API keys the vendor issued. Only the SHA-256 hash of a key is stored. |

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /v1/availability | pushAvailability |
| GET | /api/v1/desk/channel/published_nights | list_published_nights |
| POST | /internal/identity/api-keys/channelKeys/verify | verifyChannelKeysApiKey |






## Runtime configuration

Runtime configuration is resolved from generated bootstrap constants, the runtime config store, and the secrets resolver. This service does not use a `.env.example` contract.

