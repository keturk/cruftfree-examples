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

### DeliveryService

![Data models: DeliveryService](ERDs/erd-DeliveryService.svg)

### OrderService

![Data models: OrderService](ERDs/erd-OrderService.svg)

### PaymentMock

![Data models: PaymentMock](ERDs/erd-PaymentMock.svg)

### RestaurantService

![Data models: RestaurantService](ERDs/erd-RestaurantService.svg)

### RouteMock

![Data models: RouteMock](ERDs/erd-RouteMock.svg)

### SmsMock

![Data models: SmsMock](ERDs/erd-SmsMock.svg)

## Entity inheritance

One diagram per service: the abstract entities each entity extends, and the traits it uses.

### DeliveryService

![Entity inheritance: DeliveryService](inheritance/DeliveryService.svg)

### OrderService

![Entity inheritance: OrderService](inheritance/OrderService.svg)

### PaymentMock

![Entity inheritance: PaymentMock](inheritance/PaymentMock.svg)

### RestaurantService

![Entity inheritance: RestaurantService](inheritance/RestaurantService.svg)

### RouteMock

![Entity inheritance: RouteMock](inheritance/RouteMock.svg)

### SmsMock

![Entity inheritance: SmsMock](inheritance/SmsMock.svg)

## API catalog

Every REST endpoint of every service.

See [api-catalog.md](api-catalog.md).
