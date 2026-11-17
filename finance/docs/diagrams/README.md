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

### AccountService

![Data models: AccountService](ERDs/erd-AccountService.svg)

### BankMock

![Data models: BankMock](ERDs/erd-BankMock.svg)

### ComplianceService

![Data models: ComplianceService](ERDs/erd-ComplianceService.svg)

### KycMock

![Data models: KycMock](ERDs/erd-KycMock.svg)

### ModelMock

![Data models: ModelMock](ERDs/erd-ModelMock.svg)

### SanctionsMock

![Data models: SanctionsMock](ERDs/erd-SanctionsMock.svg)

### TransactionService

![Data models: TransactionService](ERDs/erd-TransactionService.svg)

## Entity inheritance

One diagram per service: the abstract entities each entity extends, and the traits it uses.

### AccountService

![Entity inheritance: AccountService](inheritance/AccountService.svg)

### BankMock

![Entity inheritance: BankMock](inheritance/BankMock.svg)

### ComplianceService

![Entity inheritance: ComplianceService](inheritance/ComplianceService.svg)

### KycMock

![Entity inheritance: KycMock](inheritance/KycMock.svg)

### ModelMock

![Entity inheritance: ModelMock](inheritance/ModelMock.svg)

### SanctionsMock

![Entity inheritance: SanctionsMock](inheritance/SanctionsMock.svg)

### TransactionService

![Entity inheritance: TransactionService](inheritance/TransactionService.svg)

## API catalog

Every REST endpoint of every service.

See [api-catalog.md](api-catalog.md).
