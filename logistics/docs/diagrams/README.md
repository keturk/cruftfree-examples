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

### CarrierMock

![Data models: CarrierMock](ERDs/erd-CarrierMock.svg)

### FleetService

![Data models: FleetService](ERDs/erd-FleetService.svg)

### GeocodeMock

![Data models: GeocodeMock](ERDs/erd-GeocodeMock.svg)

### NoticeService

![Data models: NoticeService](ERDs/erd-NoticeService.svg)

### RouteService

![Data models: RouteService](ERDs/erd-RouteService.svg)

### ShipmentService

![Data models: ShipmentService](ERDs/erd-ShipmentService.svg)

### SmsMock

![Data models: SmsMock](ERDs/erd-SmsMock.svg)

## Entity inheritance

One diagram per service: the abstract entities each entity extends, and the traits it uses.

### CarrierMock

![Entity inheritance: CarrierMock](inheritance/CarrierMock.svg)

### FleetService

![Entity inheritance: FleetService](inheritance/FleetService.svg)

### GeocodeMock

![Entity inheritance: GeocodeMock](inheritance/GeocodeMock.svg)

### NoticeService

![Entity inheritance: NoticeService](inheritance/NoticeService.svg)

### RouteService

![Entity inheritance: RouteService](inheritance/RouteService.svg)

### ShipmentService

![Entity inheritance: ShipmentService](inheritance/ShipmentService.svg)

### SmsMock

![Entity inheritance: SmsMock](inheritance/SmsMock.svg)

## API catalog

Every REST endpoint of every service.

See [api-catalog.md](api-catalog.md).
