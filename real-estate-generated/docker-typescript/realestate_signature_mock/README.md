# realestate.SignatureMock

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
| VendorEnvelope | createdAt, updatedAt, id, signerName, documentTitle, status, settledAt, documentBody, signerEmail, envelopeId, idempotencyKey | id | A document waiting for a signature. |
| ApiKey | createdAt, updatedAt, id, keyHash, ownerId, scopes, isActive, expiresAt, lastUsedAt | id | API keys the vendor issued. Only the SHA-256 hash of a key is stored. |

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /v1/envelopes | sendEnvelope |
| GET | /v1/envelopes/:id | envelopeById |
| GET | /api/v1/desk/signature/vendor_envelopes | list_vendor_envelopes |
| POST | /api/v1/desk/signature/sign/:id | sign |
| POST | /api/v1/desk/signature/decline/:id | decline |
| POST | /internal/identity/api-keys/signatureKeys/verify | verifySignatureKeysApiKey |






## Runtime configuration

Runtime configuration is resolved from generated bootstrap constants, the runtime config store, and the secrets resolver. This service does not use a `.env.example` contract.

