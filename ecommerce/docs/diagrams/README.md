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

### EmailMock

![Data models: EmailMock](ERDs/erd-EmailMock.svg)

### NotificationService

![Data models: NotificationService](ERDs/erd-NotificationService.svg)

### OrderService

![Data models: OrderService](ERDs/erd-OrderService.svg)

### PaymentMock

![Data models: PaymentMock](ERDs/erd-PaymentMock.svg)

### PaymentService

![Data models: PaymentService](ERDs/erd-PaymentService.svg)

### ProductService

![Data models: ProductService](ERDs/erd-ProductService.svg)

### ShippingService

![Data models: ShippingService](ERDs/erd-ShippingService.svg)

### UserService

![Data models: UserService](ERDs/erd-UserService.svg)

## Entity inheritance

One diagram per service: the abstract entities each entity extends, and the traits it uses.

### CarrierMock

![Entity inheritance: CarrierMock](inheritance/CarrierMock.svg)

### EmailMock

![Entity inheritance: EmailMock](inheritance/EmailMock.svg)

### NotificationService

![Entity inheritance: NotificationService](inheritance/NotificationService.svg)

### OrderService

![Entity inheritance: OrderService](inheritance/OrderService.svg)

### PaymentMock

![Entity inheritance: PaymentMock](inheritance/PaymentMock.svg)

### PaymentService

![Entity inheritance: PaymentService](inheritance/PaymentService.svg)

### ProductService

![Entity inheritance: ProductService](inheritance/ProductService.svg)

### ShippingService

![Entity inheritance: ShippingService](inheritance/ShippingService.svg)

### UserService

![Entity inheritance: UserService](inheritance/UserService.svg)

## API catalog

Every REST endpoint of every service.

See [api-catalog.md](api-catalog.md).
