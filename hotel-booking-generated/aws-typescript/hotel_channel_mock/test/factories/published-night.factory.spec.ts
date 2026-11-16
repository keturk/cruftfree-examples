import { buildPublishedNight } from './published-night.factory';

describe('buildPublishedNight', () => {
  it("entity_factory/channelDb/PublishedNight/valid_instance", () => {
    const result = buildPublishedNight();
    expect(result).toBeDefined();
    expect(result.roomType).toBeDefined();
    expect(result.night).toBeDefined();
    expect(result.left).toBeDefined();
    expect(result.nightlyRate).toBeDefined();
    expect(result.receivedAt).toBeDefined();
  });

  it("entity_factory/channelDb/PublishedNight/applies_overrides", () => {
    const overrides = {
      roomType: 'test',
    };
    const result = buildPublishedNight(overrides);
    expect(result.roomType).toBe(overrides.roomType);
  });

  it("entity_factory/channelDb/PublishedNight/distinct_instances", () => {
    const a = buildPublishedNight();
    const b = buildPublishedNight();
    expect(a).not.toBe(b);
  });
});
