import { Stay } from '../../src/hotel_stay_service/entities/stay_db/stay.entity';

/**
 * Build a partial Stay with sensible defaults for testing.
 * Override any field via the `overrides` parameter.
 */
export function buildStay(
  overrides?: Partial<Stay>,
): Partial<Stay> {
  return {
    code: `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`,
    roomTypeId: crypto.randomUUID(),
    roomTypeName: 'test',
    roomNumber: 'test',
    guestId: 'test',
    guestName: 'test',
    guestEmail: 'user@example.com',
    arrival: '2025-01-15',
    departure: '2025-01-15',
    nights: 42,
    guests: 42,
    total: '99.99',
    holdUntil: new Date('2025-01-15T12:00:00Z'),
    chargeId: 'test',
    deskNote: 'test',
    ...overrides,
  };
}
