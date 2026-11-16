import { Neighbourhood } from '../../src/realestate_listing_service/entities/listing_db/neighbourhood.entity';

/**
 * Build a partial Neighbourhood with sensible defaults for testing.
 * Override any field via the `overrides` parameter.
 */
export function buildNeighbourhood(
  overrides?: Partial<Neighbourhood>,
): Partial<Neighbourhood> {
  return {
    name: `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`,
    city: 'test',
    latitude: 3.14,
    longitude: 3.14,
    ...overrides,
  };
}
