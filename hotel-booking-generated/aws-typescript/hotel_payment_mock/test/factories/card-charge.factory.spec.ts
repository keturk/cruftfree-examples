import { buildCardCharge } from './card-charge.factory';

describe('buildCardCharge', () => {
  it("entity_factory/paymentDb/CardCharge/valid_instance", () => {
    const result = buildCardCharge();
    expect(result).toBeDefined();
    expect(result.reference).toBeDefined();
    expect(result.amount).toBeDefined();
    expect(result.currency).toBeDefined();
    expect(result.status).toBeDefined();
    expect(result.declineReason).toBeDefined();
    expect(result.chargeId).toBeDefined();
    expect(result.idempotencyKey).toBeDefined();
  });

  it("entity_factory/paymentDb/CardCharge/applies_overrides", () => {
    const overrides = {
      reference: 'test',
    };
    const result = buildCardCharge(overrides);
    expect(result.reference).toBe(overrides.reference);
  });

  it("entity_factory/paymentDb/CardCharge/distinct_instances", () => {
    const a = buildCardCharge();
    const b = buildCardCharge();
    expect(a).not.toBe(b);
  });
});
