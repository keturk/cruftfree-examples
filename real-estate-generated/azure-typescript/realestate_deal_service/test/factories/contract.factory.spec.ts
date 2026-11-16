import { buildContract } from './contract.factory';

describe('buildContract', () => {
  it("entity_factory/dealDb/Contract/valid_instance", () => {
    const result = buildContract();
    expect(result).toBeDefined();
    expect(result.listingTitle).toBeDefined();
    expect(result.buyerName).toBeDefined();
    expect(result.price).toBeDefined();
    expect(result.signedAt).toBeDefined();
    expect(result.envelopeId).toBeDefined();
    expect(result.listingId).toBeDefined();
    expect(result.offerId).toBeDefined();
    expect(result.buyerEmail).toBeDefined();
    expect(result.agentEmail).toBeDefined();
  });

  it("entity_factory/dealDb/Contract/applies_overrides", () => {
    const overrides = {
      listingTitle: 'test',
    };
    const result = buildContract(overrides);
    expect(result.listingTitle).toBe(overrides.listingTitle);
  });

  it("entity_factory/dealDb/Contract/distinct_instances", () => {
    const a = buildContract();
    const b = buildContract();
    expect(a).not.toBe(b);
  });
});
