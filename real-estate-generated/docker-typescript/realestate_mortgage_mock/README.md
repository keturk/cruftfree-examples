# realestate.MortgageMock

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
| LenderAnswer | createdAt, updatedAt, id, applicantName, amount, decision, reference, idempotencyKey, applicantEmail | id | An answer the lender gave. |
| ApiKey | createdAt, updatedAt, id, keyHash, ownerId, scopes, isActive, expiresAt, lastUsedAt | id | API keys the vendor issued. Only the SHA-256 hash of a key is stored. |

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /v1/preapprovals | preapprove |
| GET | /api/v1/desk/mortgage/lender_answers | list_lender_answers |
| POST | /internal/identity/api-keys/mortgageKeys/verify | verifyMortgageKeysApiKey |






## Runtime configuration

Runtime configuration is resolved from generated bootstrap constants, the runtime config store, and the secrets resolver. This service does not use a `.env.example` contract.

