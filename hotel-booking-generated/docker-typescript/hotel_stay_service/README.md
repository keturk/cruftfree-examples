# hotel.StayService

Version: 1.0.0
## Quick start

```bash
# Install dependencies
# See scripts/install.sh

# Run service (port 8001)
# See scripts/dev.sh
```

## Entities

| Entity | Fields | Primary key | Description |
|--------|--------|-------------|-------------|
| RoomType | createdAt, updatedAt, id, name, summary, description, sleeps, nightlyRate, inventory, listed | id | What a guest chooses. |
| Room | createdAt, updatedAt, id, number, roomTypeId, roomTypeName, floor, condition | id | A door with a number. Only the desk thinks about these. |
| Stay | createdAt, updatedAt, id, code, roomTypeId, roomTypeName, roomNumber, guestId, guestName, guestEmail, arrival, departure, nights, guests, total, status, holdUntil, chargeId, deskNote | id |  |

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/stays/room-types | roomTypes |
| GET | /api/v1/stays/room-types/:id | roomType |
| POST | /api/v1/stays/search | search |
| POST | /api/v1/stays/hold | hold |
| POST | /api/v1/stays/pay | pay |
| GET | /api/v1/stays/mine | mine |
| GET | /api/v1/stays/mine/:id | oneOfMine |
| POST | /api/v1/stays/mine/:id/cancel | cancelMine |
| GET | /api/v1/desk/room_types | list_room_types |
| GET | /api/v1/desk/room_types/:id | get_room_type |
| POST | /api/v1/desk/room_types | create_room_type |
| PUT | /api/v1/desk/room_types/:id | update_room_type |
| DELETE | /api/v1/desk/room_types/:id | delete_room_type |
| GET | /api/v1/desk/stays | list_stays |
| GET | /api/v1/desk/today | today |
| GET | /api/v1/desk/arrivals | arrivals |
| GET | /api/v1/desk/departures | departures |
| GET | /api/v1/desk/occupancy | occupancy |
| GET | /api/v1/desk/calendar | calendar |
| GET | /api/v1/desk/stays/:id | oneStay |
| GET | /api/v1/desk/stays/:id/free-rooms | freeRooms |
| POST | /api/v1/desk/check-in | checkIn |
| POST | /api/v1/desk/stays/:id/check-out | checkOut |
| POST | /api/v1/desk/stays/:id/cancel | cancelAtDesk |
| POST | /api/v1/desk/note | addNote |
| GET | /api/v1/desk/rooms | rooms |
| POST | /api/v1/desk/rooms/:id/condition | setCondition |

## Events

| Topic | Events |
|-------|--------|
| StayEvents | StayConfirmed, StayCancelled, HoldLapsed, ArrivingTomorrow, GuestLeft |





## Runtime configuration

Runtime configuration is resolved from generated bootstrap constants, the runtime config store, and the secrets resolver. This service does not use a `.env.example` contract.

