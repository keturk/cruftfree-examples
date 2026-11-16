import { RoomType } from '../../src/hotel_stay_service/entities/stay_db/room-type.entity';

/**
 * Build a partial RoomType with sensible defaults for testing.
 * Override any field via the `overrides` parameter.
 */
export function buildRoomType(
  overrides?: Partial<RoomType>,
): Partial<RoomType> {
  return {
    name: `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`,
    summary: 'test',
    description: 'test',
    sleeps: 42,
    nightlyRate: '99.99',
    inventory: 42,
    ...overrides,
  };
}
