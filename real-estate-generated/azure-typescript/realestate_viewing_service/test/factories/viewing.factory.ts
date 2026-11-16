import { Viewing } from '../../src/realestate_viewing_service/entities/viewing_db/viewing.entity';

/**
 * Build a partial Viewing with sensible defaults for testing.
 * Override any field via the `overrides` parameter.
 */
export function buildViewing(
  overrides?: Partial<Viewing>,
): Partial<Viewing> {
  return {
    startsAt: new Date('2025-01-15T12:00:00Z'),
    endsAt: new Date('2025-01-15T12:00:00Z'),
    listingTitle: 'test',
    buyerName: 'test',
    agentName: 'test',
    note: 'test',
    listingId: crypto.randomUUID(),
    buyerEmail: 'user@example.com',
    agentEmail: 'user@example.com',
    ...overrides,
  };
}
