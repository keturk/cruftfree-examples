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

### CourseService

![Data models: CourseService](ERDs/erd-CourseService.svg)

### EmailMock

![Data models: EmailMock](ERDs/erd-EmailMock.svg)

### EnrollmentService

![Data models: EnrollmentService](ERDs/erd-EnrollmentService.svg)

### ModelMock

![Data models: ModelMock](ERDs/erd-ModelMock.svg)

### PaymentMock

![Data models: PaymentMock](ERDs/erd-PaymentMock.svg)

### TutorService

![Data models: TutorService](ERDs/erd-TutorService.svg)

## Entity inheritance

One diagram per service: the abstract entities each entity extends, and the traits it uses.

### CourseService

![Entity inheritance: CourseService](inheritance/CourseService.svg)

### EmailMock

![Entity inheritance: EmailMock](inheritance/EmailMock.svg)

### EnrollmentService

![Entity inheritance: EnrollmentService](inheritance/EnrollmentService.svg)

### ModelMock

![Entity inheritance: ModelMock](inheritance/ModelMock.svg)

### PaymentMock

![Entity inheritance: PaymentMock](inheritance/PaymentMock.svg)

### TutorService

![Entity inheritance: TutorService](inheritance/TutorService.svg)

## API catalog

Every REST endpoint of every service.

See [api-catalog.md](api-catalog.md).
