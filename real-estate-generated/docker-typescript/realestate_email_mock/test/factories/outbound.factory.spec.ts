import { buildOutbound } from './outbound.factory';

describe('buildOutbound', () => {
  it("entity_factory/emailDb/Outbound/valid_instance", () => {
    const result = buildOutbound();
    expect(result).toBeDefined();
    expect(result.recipient).toBeDefined();
    expect(result.subject).toBeDefined();
    expect(result.body).toBeDefined();
    expect(result.status).toBeDefined();
    expect(result.deliveryId).toBeDefined();
    expect(result.idempotencyKey).toBeDefined();
  });

  it("entity_factory/emailDb/Outbound/applies_overrides", () => {
    const overrides = {
      recipient: 'test',
    };
    const result = buildOutbound(overrides);
    expect(result.recipient).toBe(overrides.recipient);
  });

  it("entity_factory/emailDb/Outbound/distinct_instances", () => {
    const a = buildOutbound();
    const b = buildOutbound();
    expect(a).not.toBe(b);
  });
});
