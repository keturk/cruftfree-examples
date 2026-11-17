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

### DistrictService

![Data models: DistrictService](ERDs/erd-DistrictService.svg)

### FacilityService

![Data models: FacilityService](ERDs/erd-FacilityService.svg)

### GeocoderMock

![Data models: GeocoderMock](ERDs/erd-GeocoderMock.svg)

### RequestService

![Data models: RequestService](ERDs/erd-RequestService.svg)

### SmsMock

![Data models: SmsMock](ERDs/erd-SmsMock.svg)

## Entity inheritance

One diagram per service: the abstract entities each entity extends, and the traits it uses.

### DistrictService

![Entity inheritance: DistrictService](inheritance/DistrictService.svg)

### FacilityService

![Entity inheritance: FacilityService](inheritance/FacilityService.svg)

### GeocoderMock

![Entity inheritance: GeocoderMock](inheritance/GeocoderMock.svg)

### RequestService

![Entity inheritance: RequestService](inheritance/RequestService.svg)

### SmsMock

![Entity inheritance: SmsMock](inheritance/SmsMock.svg)

## API catalog

Every REST endpoint of every service.

See [api-catalog.md](api-catalog.md).
