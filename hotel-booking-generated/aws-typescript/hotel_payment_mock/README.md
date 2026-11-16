# hotel.PaymentMock

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
| CardCharge | createdAt, updatedAt, id, reference, amount, currency, status, declineReason, chargeId, idempotencyKey | id | A charge the vendor answered. |
| ApiKey | createdAt, updatedAt, id, keyHash, ownerId, scopes, isActive, expiresAt, lastUsedAt | id | API keys the vendor issued. Only the SHA-256 hash of a key is stored. |

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /v1/charges | createCharge |
| POST | /v1/refunds | refundCharge |
| GET | /api/v1/desk/payment/card_charges | list_card_charges |
| POST | /internal/identity/api-keys/paymentKeys/verify | verifyPaymentKeysApiKey |






## Runtime configuration

Runtime configuration is resolved from generated bootstrap constants, the runtime config store, and the secrets resolver. This service does not use a `.env.example` contract.

