import { Room } from '../../src/hotel_stay_service/entities/stay_db/room.entity';

/**
 * Build a partial Room with sensible defaults for testing.
 * Override any field via the `overrides` parameter.
 */
export function buildRoom(
  overrides?: Partial<Room>,
): Partial<Room> {
  return {
    number: `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 3)}`,
    roomTypeId: crypto.randomUUID(),
    roomTypeName: 'test',
    floor: 42,
    ...overrides,
  };
}
