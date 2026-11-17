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

### DeviceService

![Data models: DeviceService](ERDs/erd-DeviceService.svg)

### FirmwareService

![Data models: FirmwareService](ERDs/erd-FirmwareService.svg)

### FleetMock

![Data models: FleetMock](ERDs/erd-FleetMock.svg)

### PagerMock

![Data models: PagerMock](ERDs/erd-PagerMock.svg)

### TelemetryService

![Data models: TelemetryService](ERDs/erd-TelemetryService.svg)

## Entity inheritance

One diagram per service: the abstract entities each entity extends, and the traits it uses.

### DeviceService

![Entity inheritance: DeviceService](inheritance/DeviceService.svg)

### FirmwareService

![Entity inheritance: FirmwareService](inheritance/FirmwareService.svg)

### FleetMock

![Entity inheritance: FleetMock](inheritance/FleetMock.svg)

### PagerMock

![Entity inheritance: PagerMock](inheritance/PagerMock.svg)

### TelemetryService

![Entity inheritance: TelemetryService](inheritance/TelemetryService.svg)

## API catalog

Every REST endpoint of every service.

See [api-catalog.md](api-catalog.md).
