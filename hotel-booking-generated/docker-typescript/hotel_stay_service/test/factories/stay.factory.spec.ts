import { buildStay } from './stay.factory';

describe('buildStay', () => {
  it("entity_factory/stayDb/Stay/valid_instance", () => {
    const result = buildStay();
    expect(result).toBeDefined();
    expect(result.code).toBeDefined();
    expect(result.roomTypeId).toBeDefined();
    expect(result.roomTypeName).toBeDefined();
    expect(result.roomNumber).toBeDefined();
    expect(result.guestId).toBeDefined();
    expect(result.guestName).toBeDefined();
    expect(result.guestEmail).toBeDefined();
    expect(result.arrival).toBeDefined();
    expect(result.departure).toBeDefined();
    expect(result.nights).toBeDefined();
    expect(result.guests).toBeDefined();
    expect(result.total).toBeDefined();
    expect(result.holdUntil).toBeDefined();
    expect(result.chargeId).toBeDefined();
    expect(result.deskNote).toBeDefined();
  });

  it("entity_factory/stayDb/Stay/applies_overrides", () => {
    const overrides = {
      code: `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`,
    };
    const result = buildStay(overrides);
    expect(result.code).toBe(overrides.code);
  });

  it("entity_factory/stayDb/Stay/distinct_instances", () => {
    const a = buildStay();
    const b = buildStay();
    expect(a).not.toBe(b);
  });
});
