import { buildNeighbourhood } from './neighbourhood.factory';

describe('buildNeighbourhood', () => {
  it("entity_factory/listingDb/Neighbourhood/valid_instance", () => {
    const result = buildNeighbourhood();
    expect(result).toBeDefined();
    expect(result.name).toBeDefined();
    expect(result.city).toBeDefined();
    expect(result.latitude).toBeDefined();
    expect(result.longitude).toBeDefined();
  });

  it("entity_factory/listingDb/Neighbourhood/applies_overrides", () => {
    const overrides = {
      name: `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`,
    };
    const result = buildNeighbourhood(overrides);
    expect(result.name).toBe(overrides.name);
  });

  it("entity_factory/listingDb/Neighbourhood/distinct_instances", () => {
    const a = buildNeighbourhood();
    const b = buildNeighbourhood();
    expect(a).not.toBe(b);
  });
});
