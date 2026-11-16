import { Offer } from '../../src/realestate_deal_service/entities/deal_db/offer.entity';
import { Financing } from '../../src/enums/financing.enum';

/**
 * Build a partial Offer with sensible defaults for testing.
 * Override any field via the `overrides` parameter.
 */
export function buildOffer(
  overrides?: Partial<Offer>,
): Partial<Offer> {
  return {
    listingTitle: 'test',
    buyerName: 'test',
    amount: '99.99',
    financing: Financing.Cash,
    lenderReference: 'test',
    listingId: crypto.randomUUID(),
    buyerEmail: 'user@example.com',
    agentEmail: 'user@example.com',
    ...overrides,
  };
}
