# hotel.EmailMock

Version: 1.0.0
## Quick start

```bash
# Install dependencies
# See scripts/install.sh

# Run service (port 8091)
# See scripts/dev.sh
```

## Entities

| Entity | Fields | Primary key | Description |
|--------|--------|-------------|-------------|
| Outbound | createdAt, updatedAt, id, recipient, subject, body, status, deliveryId, idempotencyKey | id | An email the vendor accepted. |
| ApiKey | createdAt, updatedAt, id, keyHash, ownerId, scopes, isActive, expiresAt, lastUsedAt | id | API keys the vendor issued. Only the SHA-256 hash of a key is stored. |

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /v1/deliveries | sendEmail |
| GET | /api/v1/desk/email/outbounds | list_outbounds |
| POST | /internal/identity/api-keys/emailKeys/verify | verifyEmailKeysApiKey |






## Runtime configuration

Runtime configuration is resolved from generated bootstrap constants, the runtime config store, and the secrets resolver. This service does not use a `.env.example` contract.

