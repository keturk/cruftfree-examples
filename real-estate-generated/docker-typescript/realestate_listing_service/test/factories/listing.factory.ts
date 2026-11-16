import { Listing } from '../../src/realestate_listing_service/entities/listing_db/listing.entity';
import { PropertyKind } from '../../src/enums/property-kind.enum';

/**
 * Build a partial Listing with sensible defaults for testing.
 * Override any field via the `overrides` parameter.
 */
export function buildListing(
  overrides?: Partial<Listing>,
): Partial<Listing> {
  return {
    title: 'test',
    neighbourhoodName: 'test',
    kind: PropertyKind.House,
    price: '99.99',
    bedrooms: 42,
    bathrooms: 42,
    areaSqm: 42,
    agentName: 'test',
    publishedAt: new Date('2025-01-15T12:00:00Z'),
    summary: 'test',
    city: 'test',
    latitude: 3.14,
    longitude: 3.14,
    agentEmail: 'user@example.com',
    ...overrides,
  };
}
