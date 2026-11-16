# cityservices.DistrictService

Version: 2.0.0
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
| District | createdAt, updatedAt, id, name, code, population, boundaryGeoJson, boundary, description | id |  |
| ZoningArea | createdAt, updatedAt, id, name, zoneCode, type, boundaryGeoJson, boundary, districtId | id |  |

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/districts/districts | list_districts |
| GET | /api/v1/districts/for-location | forLocation |
| GET | /api/v1/districts/zoning | zoningAt |
| GET | /api/v1/districts/facts | facts |






## Runtime configuration

Runtime configuration is resolved from generated bootstrap constants, the runtime config store, and the secrets resolver. This service does not use a `.env.example` contract.

