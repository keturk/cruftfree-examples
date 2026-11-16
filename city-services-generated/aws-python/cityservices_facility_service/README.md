# cityservices.FacilityService

Version: 2.0.0
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
| Facility | createdAt, updatedAt, id, name, type, latitude, longitude, location, address, phone, isOperational | id |  |
| Park | createdAt, updatedAt, id, name, boundaryGeoJson, boundary, isOpen, amenities | id |  |

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/facilities/facilities | list_facilities |
| GET | /api/v1/facilities/map | pins |
| GET | /api/v1/facilities/nearby | nearby |
| GET | /api/v1/facilities/parks | parks |
| POST | /api/v1/facilities/:id/operational | setOperational |






## Runtime configuration

Runtime configuration is resolved from generated bootstrap constants, the runtime config store, and the secrets resolver. This service does not use a `.env.example` contract.

