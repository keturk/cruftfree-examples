# cityservices.SmsMock

Version: 1.0.0
## Quick start

```bash
# Install dependencies
# See scripts/install.sh

# Run service (port 8090)
# See scripts/dev.sh
```

## Entities

| Entity | Fields | Primary key | Description |
|--------|--------|-------------|-------------|
| SentSms | createdAt, updatedAt, id, messageId, idempotencyKey, recipient, body, status | id | A text the vendor accepted. |
| ApiKey | createdAt, updatedAt, id, keyHash, ownerId, scopes, isActive, expiresAt, lastUsedAt | id | API keys the vendor issued. Only the SHA-256 hash of a key is stored. |

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /v1/messages | post |
| GET | /api/v1/desk/sms/sent_sms | list_sent_sms |
| POST | /internal/identity/api-keys/smsKeys/verify | verifySmsKeysApiKey |






## Runtime configuration

Runtime configuration is resolved from generated bootstrap constants, the runtime config store, and the secrets resolver. This service does not use a `.env.example` contract.

