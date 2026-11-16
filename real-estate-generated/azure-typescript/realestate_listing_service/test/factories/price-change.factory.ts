import { PriceChange } from '../../src/realestate_listing_service/entities/listing_db/price-change.entity';

/**
 * Build a partial PriceChange with sensible defaults for testing.
 * Override any field via the `overrides` parameter.
 */
export function buildPriceChange(
  overrides?: Partial<PriceChange>,
): Partial<PriceChange> {
  return {
    listingId: crypto.randomUUID(),
    oldPrice: '99.99',
    newPrice: '99.99',
    ...overrides,
  };
}
