import { buildViewing } from './viewing.factory';

describe('buildViewing', () => {
  it("entity_factory/viewingDb/Viewing/valid_instance", () => {
    const result = buildViewing();
    expect(result).toBeDefined();
    expect(result.startsAt).toBeDefined();
    expect(result.endsAt).toBeDefined();
    expect(result.listingTitle).toBeDefined();
    expect(result.buyerName).toBeDefined();
    expect(result.agentName).toBeDefined();
    expect(result.note).toBeDefined();
    expect(result.listingId).toBeDefined();
    expect(result.buyerEmail).toBeDefined();
    expect(result.agentEmail).toBeDefined();
  });

  it("entity_factory/viewingDb/Viewing/applies_overrides", () => {
    const overrides = {
      startsAt: new Date('2025-01-15T12:00:00Z'),
    };
    const result = buildViewing(overrides);
    expect(result.startsAt).toEqual(overrides.startsAt);
  });

  it("entity_factory/viewingDb/Viewing/distinct_instances", () => {
    const a = buildViewing();
    const b = buildViewing();
    expect(a).not.toBe(b);
  });
});
