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

### ChatMock

![Data models: ChatMock](ERDs/erd-ChatMock.svg)

### EmailMock

![Data models: EmailMock](ERDs/erd-EmailMock.svg)

### NoticeService

![Data models: NoticeService](ERDs/erd-NoticeService.svg)

### ProjectService

![Data models: ProjectService](ERDs/erd-ProjectService.svg)

### TaskService

![Data models: TaskService](ERDs/erd-TaskService.svg)

## Entity inheritance

One diagram per service: the abstract entities each entity extends, and the traits it uses.

### ChatMock

![Entity inheritance: ChatMock](inheritance/ChatMock.svg)

### EmailMock

![Entity inheritance: EmailMock](inheritance/EmailMock.svg)

### NoticeService

![Entity inheritance: NoticeService](inheritance/NoticeService.svg)

### ProjectService

![Entity inheritance: ProjectService](inheritance/ProjectService.svg)

### TaskService

![Entity inheritance: TaskService](inheritance/TaskService.svg)

## API catalog

Every REST endpoint of every service.

See [api-catalog.md](api-catalog.md).
