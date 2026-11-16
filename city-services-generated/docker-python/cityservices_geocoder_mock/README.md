# cityservices.GeocoderMock

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
| KnownAddress | createdAt, updatedAt, id, address, formattedAddress, latitude, longitude | id | An address the vendor recognises. The lookup key is lower case. |
| Lookup | createdAt, updatedAt, id, query, matched | id | One lookup the vendor answered. |
| ApiKey | createdAt, updatedAt, id, keyHash, ownerId, scopes, isActive, expiresAt, lastUsedAt | id | API keys the vendor issued. Only the SHA-256 hash of a key is stored. |

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /v1/geocode | post |
| GET | /api/v1/desk/geocoder/lookups | list_lookups |
| GET | /api/v1/desk/geocoder/known_addresses | list_known_addresses |
| POST | /api/v1/desk/geocoder/known_addresses | create_known_address |
| DELETE | /api/v1/desk/geocoder/known_addresses/:id | delete_known_address |
| POST | /internal/identity/api-keys/geocoderKeys/verify | verifyGeocoderKeysApiKey |






## Runtime configuration

Runtime configuration is resolved from generated bootstrap constants, the runtime config store, and the secrets resolver. This service does not use a `.env.example` contract.

