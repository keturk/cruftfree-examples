import { buildListing } from './listing.factory';

describe('buildListing', () => {
  it("entity_factory/listingDb/Listing/valid_instance", () => {
    const result = buildListing();
    expect(result).toBeDefined();
    expect(result.title).toBeDefined();
    expect(result.neighbourhoodName).toBeDefined();
    expect(result.kind).toBeDefined();
    expect(result.price).toBeDefined();
    expect(result.bedrooms).toBeDefined();
    expect(result.bathrooms).toBeDefined();
    expect(result.areaSqm).toBeDefined();
    expect(result.agentName).toBeDefined();
    expect(result.publishedAt).toBeDefined();
    expect(result.summary).toBeDefined();
    expect(result.city).toBeDefined();
    expect(result.latitude).toBeDefined();
    expect(result.longitude).toBeDefined();
    expect(result.agentEmail).toBeDefined();
  });

  it("entity_factory/listingDb/Listing/applies_overrides", () => {
    const overrides = {
      title: 'test',
    };
    const result = buildListing(overrides);
    expect(result.title).toBe(overrides.title);
  });

  it("entity_factory/listingDb/Listing/distinct_instances", () => {
    const a = buildListing();
    const b = buildListing();
    expect(a).not.toBe(b);
  });
});
