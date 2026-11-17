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

### AuthorService

![Data models: AuthorService](ERDs/erd-AuthorService.svg)

### CommentService

![Data models: CommentService](ERDs/erd-CommentService.svg)

### ContentService

![Data models: ContentService](ERDs/erd-ContentService.svg)

### MailMock

![Data models: MailMock](ERDs/erd-MailMock.svg)

### ModerationMock

![Data models: ModerationMock](ERDs/erd-ModerationMock.svg)

### NewsletterService

![Data models: NewsletterService](ERDs/erd-NewsletterService.svg)

## Entity inheritance

One diagram per service: the abstract entities each entity extends, and the traits it uses.

### AuthorService

![Entity inheritance: AuthorService](inheritance/AuthorService.svg)

### CommentService

![Entity inheritance: CommentService](inheritance/CommentService.svg)

### ContentService

![Entity inheritance: ContentService](inheritance/ContentService.svg)

### MailMock

![Entity inheritance: MailMock](inheritance/MailMock.svg)

### ModerationMock

![Entity inheritance: ModerationMock](inheritance/ModerationMock.svg)

### NewsletterService

![Entity inheritance: NewsletterService](inheritance/NewsletterService.svg)

## API catalog

Every REST endpoint of every service.

See [api-catalog.md](api-catalog.md).
