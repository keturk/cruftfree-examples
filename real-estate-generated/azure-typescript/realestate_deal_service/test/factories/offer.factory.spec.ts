import { buildOffer } from './offer.factory';

describe('buildOffer', () => {
  it("entity_factory/dealDb/Offer/valid_instance", () => {
    const result = buildOffer();
    expect(result).toBeDefined();
    expect(result.listingTitle).toBeDefined();
    expect(result.buyerName).toBeDefined();
    expect(result.amount).toBeDefined();
    expect(result.financing).toBeDefined();
    expect(result.lenderReference).toBeDefined();
    expect(result.listingId).toBeDefined();
    expect(result.buyerEmail).toBeDefined();
    expect(result.agentEmail).toBeDefined();
  });

  it("entity_factory/dealDb/Offer/applies_overrides", () => {
    const overrides = {
      listingTitle: 'test',
    };
    const result = buildOffer(overrides);
    expect(result.listingTitle).toBe(overrides.listingTitle);
  });

  it("entity_factory/dealDb/Offer/distinct_instances", () => {
    const a = buildOffer();
    const b = buildOffer();
    expect(a).not.toBe(b);
  });
});
