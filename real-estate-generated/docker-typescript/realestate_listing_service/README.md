# realestate.ListingService

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
| Neighbourhood | createdAt, updatedAt, id, name, city, latitude, longitude | id | A neighbourhood the agency works in. Choosing one places a home on the map. |
| Listing | createdAt, updatedAt, id, title, neighbourhoodName, kind, price, bedrooms, bathrooms, areaSqm, status, agentName, publishedAt, summary, city, latitude, longitude, agentEmail | id |  |
| PriceChange | createdAt, updatedAt, id, listingId, oldPrice, newPrice | id | Every price a home has asked. Never changed once written. |

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/homes | onTheMarket |
| GET | /api/v1/homes/search | search |
| GET | /api/v1/homes/pins | pins |
| GET | /api/v1/homes/home/:id | home |
| GET | /api/v1/agent/listings/listings | list_listings |
| GET | /api/v1/agent/listings/neighbourhoods | list_neighbourhoods |
| GET | /api/v1/agent/listings/summary | summary |
| GET | /api/v1/agent/listings/page/:id | page |
| POST | /api/v1/agent/listings/new | createListing |
| POST | /api/v1/agent/listings/publish/:id | publish |
| POST | /api/v1/agent/listings/withdraw/:id | withdraw |
| POST | /api/v1/agent/listings/price | changePrice |
| GET | /internal/listings/facts/:id | facts |
| POST | /internal/listings/under-offer | markUnderOffer |
| POST | /internal/listings/sold | markSold |
| POST | /internal/listings/reopen | reopen |

## Events

| Topic | Events |
|-------|--------|
| ListingEvents | ListingPriceChanged |





## Runtime configuration

Runtime configuration is resolved from generated bootstrap constants, the runtime config store, and the secrets resolver. This service does not use a `.env.example` contract.

