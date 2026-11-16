import { Contract } from '../../src/realestate_deal_service/entities/deal_db/contract.entity';

/**
 * Build a partial Contract with sensible defaults for testing.
 * Override any field via the `overrides` parameter.
 */
export function buildContract(
  overrides?: Partial<Contract>,
): Partial<Contract> {
  return {
    listingTitle: 'test',
    buyerName: 'test',
    price: '99.99',
    signedAt: new Date('2025-01-15T12:00:00Z'),
    envelopeId: 'test',
    listingId: crypto.randomUUID(),
    offerId: crypto.randomUUID(),
    buyerEmail: 'user@example.com',
    agentEmail: 'user@example.com',
    ...overrides,
  };
}
