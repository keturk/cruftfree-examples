# realestate.DealService

Version: 2.0.0
## Quick start

```bash
# Install dependencies
# See scripts/install.sh

# Run service (port 8003)
# See scripts/dev.sh
```

## Entities

| Entity | Fields | Primary key | Description |
|--------|--------|-------------|-------------|
| Offer | createdAt, updatedAt, id, listingTitle, buyerName, amount, financing, status, lenderReference, listingId, buyerEmail, agentEmail | id |  |
| Contract | createdAt, updatedAt, id, listingTitle, buyerName, price, status, signedAt, envelopeId, listingId, offerId, buyerEmail, agentEmail | id |  |

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/offers/mine | mine |
| GET | /api/v1/offers/my-contracts | myContracts |
| POST | /api/v1/offers/make | makeOffer |
| POST | /api/v1/offers/withdraw/:id | withdraw |
| GET | /api/v1/agent/deals/offers | list_offers |
| GET | /api/v1/agent/deals/contracts | list_contracts |
| GET | /api/v1/agent/deals/summary | summary |
| POST | /api/v1/agent/deals/accept/:id | accept |
| POST | /api/v1/agent/deals/reject/:id | reject |






## Runtime configuration

Runtime configuration is resolved from generated bootstrap constants, the runtime config store, and the secrets resolver. This service does not use a `.env.example` contract.

