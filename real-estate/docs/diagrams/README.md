# Diagrams

Drawn from this application's `.cfree` specification by CruftFree's `visualize` script. They are generated files: change the specification and run the script again rather than editing them.

## System context

Who uses the system, the services they reach, and the external systems behind them.

![System context](system-context.svg)

## Service map

Services, the calls between them, and the infrastructure they share.

![Service map](service-map.svg)

## Event flow

Events each service publishes, and the services that handle them.

![Event flow](event-flow.svg)

## Infrastructure by service

The databases, caches, brokers, storage and jobs each service declares.

![Infrastructure by service](infrastructure.svg)

## Data models

One entity-relationship diagram per service: entities, keys and relationships.

### DealService

![Data models: DealService](ERDs/erd-DealService.svg)

### EmailMock

![Data models: EmailMock](ERDs/erd-EmailMock.svg)

### ListingService

![Data models: ListingService](ERDs/erd-ListingService.svg)

### MortgageMock

![Data models: MortgageMock](ERDs/erd-MortgageMock.svg)

### SignatureMock

![Data models: SignatureMock](ERDs/erd-SignatureMock.svg)

### ViewingService

![Data models: ViewingService](ERDs/erd-ViewingService.svg)

## Entity inheritance

One diagram per service: the abstract entities each entity extends, and the traits it uses.

### DealService

![Entity inheritance: DealService](inheritance/DealService.svg)

### EmailMock

![Entity inheritance: EmailMock](inheritance/EmailMock.svg)

### ListingService

![Entity inheritance: ListingService](inheritance/ListingService.svg)

### MortgageMock

![Entity inheritance: MortgageMock](inheritance/MortgageMock.svg)

### SignatureMock

![Entity inheritance: SignatureMock](inheritance/SignatureMock.svg)

### ViewingService

![Entity inheritance: ViewingService](inheritance/ViewingService.svg)

## API catalog

Every REST endpoint of every service.

See [api-catalog.md](api-catalog.md).
