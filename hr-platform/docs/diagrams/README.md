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

## CQRS data flow

Commands, the events projections handle, the views they write, and the queries that read them.

![CQRS data flow](cqrs-flow.svg)

## Infrastructure by service

The databases, caches, brokers, storage and jobs each service declares.

![Infrastructure by service](infrastructure.svg)

## Data models

One entity-relationship diagram per service: entities, keys and relationships.

### BankMock

![Data models: BankMock](ERDs/erd-BankMock.svg)

### CheckMock

![Data models: CheckMock](ERDs/erd-CheckMock.svg)

### EmployeeService

![Data models: EmployeeService](ERDs/erd-EmployeeService.svg)

### PayrollService

![Data models: PayrollService](ERDs/erd-PayrollService.svg)

### RecruitmentService

![Data models: RecruitmentService](ERDs/erd-RecruitmentService.svg)

### SignatureMock

![Data models: SignatureMock](ERDs/erd-SignatureMock.svg)

## Entity inheritance

One diagram per service: the abstract entities each entity extends, and the traits it uses.

### BankMock

![Entity inheritance: BankMock](inheritance/BankMock.svg)

### CheckMock

![Entity inheritance: CheckMock](inheritance/CheckMock.svg)

### EmployeeService

![Entity inheritance: EmployeeService](inheritance/EmployeeService.svg)

### PayrollService

![Entity inheritance: PayrollService](inheritance/PayrollService.svg)

### RecruitmentService

![Entity inheritance: RecruitmentService](inheritance/RecruitmentService.svg)

### SignatureMock

![Entity inheritance: SignatureMock](inheritance/SignatureMock.svg)

## API catalog

Every REST endpoint of every service.

See [api-catalog.md](api-catalog.md).
