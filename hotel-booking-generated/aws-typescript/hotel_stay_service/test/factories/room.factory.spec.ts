import { buildRoom } from './room.factory';

describe('buildRoom', () => {
  it("entity_factory/stayDb/Room/valid_instance", () => {
    const result = buildRoom();
    expect(result).toBeDefined();
    expect(result.number).toBeDefined();
    expect(result.roomTypeId).toBeDefined();
    expect(result.roomTypeName).toBeDefined();
    expect(result.floor).toBeDefined();
  });

  it("entity_factory/stayDb/Room/applies_overrides", () => {
    const overrides = {
      number: `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 3)}`,
    };
    const result = buildRoom(overrides);
    expect(result.number).toBe(overrides.number);
  });

  it("entity_factory/stayDb/Room/distinct_instances", () => {
    const a = buildRoom();
    const b = buildRoom();
    expect(a).not.toBe(b);
  });
});
