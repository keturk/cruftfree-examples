import { buildPriceChange } from './price-change.factory';

describe('buildPriceChange', () => {
  it("entity_factory/listingDb/PriceChange/valid_instance", () => {
    const result = buildPriceChange();
    expect(result).toBeDefined();
    expect(result.listingId).toBeDefined();
    expect(result.oldPrice).toBeDefined();
    expect(result.newPrice).toBeDefined();
  });

  it("entity_factory/listingDb/PriceChange/applies_overrides", () => {
    const overrides = {
      listingId: crypto.randomUUID(),
    };
    const result = buildPriceChange(overrides);
    expect(result.listingId).toBe(overrides.listingId);
  });

  it("entity_factory/listingDb/PriceChange/distinct_instances", () => {
    const a = buildPriceChange();
    const b = buildPriceChange();
    expect(a).not.toBe(b);
  });
});
