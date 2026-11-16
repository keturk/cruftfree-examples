import { validate } from 'class-validator';
import { instanceToPlain, plainToInstance } from 'class-transformer';
import { RefundChargeRequest } from '../src/dto/refund-charge-request.struct';

describe('RefundChargeRequest Struct', () => {
  function buildValidPayload(): Record<string, unknown> {
    return {
      chargeId: 'sample_text',
      amount: '9.99',
      idempotencyKey: 'world',
    };
  }

  it("struct/RefundChargeRequest/create_instance", () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(RefundChargeRequest, payload);
    expect(instance).toBeDefined();
    expect(instance.chargeId).toBeDefined();
    expect(instance.amount).toBeDefined();
    expect(instance.idempotencyKey).toBeDefined();
  });

  it("struct/RefundChargeRequest/passes_validation", async () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(RefundChargeRequest, payload);
    const errors = await validate(instance);
    expect(errors.length).toBe(0);
  });

  it("struct/RefundChargeRequest/chargeId/required", async () => {
    const payload = buildValidPayload();
    delete payload.chargeId;
    const instance = plainToInstance(RefundChargeRequest, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/RefundChargeRequest/amount/required", async () => {
    const payload = buildValidPayload();
    delete payload.amount;
    const instance = plainToInstance(RefundChargeRequest, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/RefundChargeRequest/idempotencyKey/required", async () => {
    const payload = buildValidPayload();
    delete payload.idempotencyKey;
    const instance = plainToInstance(RefundChargeRequest, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/RefundChargeRequest/serialization_round_trip", () => {
    const instance = plainToInstance(RefundChargeRequest, buildValidPayload());
    const restored = plainToInstance(RefundChargeRequest, instanceToPlain(instance));
    expect(restored).toEqual(instance);
  });
});
