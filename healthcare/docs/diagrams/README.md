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

### AppointmentService

![Data models: AppointmentService](ERDs/erd-AppointmentService.svg)

### InsurerMock

![Data models: InsurerMock](ERDs/erd-InsurerMock.svg)

### PatientService

![Data models: PatientService](ERDs/erd-PatientService.svg)

### PharmacyMock

![Data models: PharmacyMock](ERDs/erd-PharmacyMock.svg)

### RecordService

![Data models: RecordService](ERDs/erd-RecordService.svg)

### SmsMock

![Data models: SmsMock](ERDs/erd-SmsMock.svg)

## Entity inheritance

One diagram per service: the abstract entities each entity extends, and the traits it uses.

### AppointmentService

![Entity inheritance: AppointmentService](inheritance/AppointmentService.svg)

### InsurerMock

![Entity inheritance: InsurerMock](inheritance/InsurerMock.svg)

### PatientService

![Entity inheritance: PatientService](inheritance/PatientService.svg)

### PharmacyMock

![Entity inheritance: PharmacyMock](inheritance/PharmacyMock.svg)

### RecordService

![Entity inheritance: RecordService](inheritance/RecordService.svg)

### SmsMock

![Entity inheritance: SmsMock](inheritance/SmsMock.svg)

## API catalog

Every REST endpoint of every service.

See [api-catalog.md](api-catalog.md).
