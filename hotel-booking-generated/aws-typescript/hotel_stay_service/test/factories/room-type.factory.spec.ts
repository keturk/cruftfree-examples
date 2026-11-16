import { buildRoomType } from './room-type.factory';

describe('buildRoomType', () => {
  it("entity_factory/stayDb/RoomType/valid_instance", () => {
    const result = buildRoomType();
    expect(result).toBeDefined();
    expect(result.name).toBeDefined();
    expect(result.summary).toBeDefined();
    expect(result.description).toBeDefined();
    expect(result.sleeps).toBeDefined();
    expect(result.nightlyRate).toBeDefined();
    expect(result.inventory).toBeDefined();
  });

  it("entity_factory/stayDb/RoomType/applies_overrides", () => {
    const overrides = {
      name: `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`,
    };
    const result = buildRoomType(overrides);
    expect(result.name).toBe(overrides.name);
  });

  it("entity_factory/stayDb/RoomType/distinct_instances", () => {
    const a = buildRoomType();
    const b = buildRoomType();
    expect(a).not.toBe(b);
  });
});
