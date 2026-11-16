import { validate } from 'class-validator';
import { instanceToPlain, plainToInstance } from 'class-transformer';
import { CreateChargeRequest } from '../src/dto/create-charge-request.struct';

describe('CreateChargeRequest Struct', () => {
  function buildValidPayload(): Record<string, unknown> {
    return {
      cardToken: 'test_string',
      amount: '4.50',
      currency: 'hel',
      reference: 'foo_bar',
      idempotencyKey: 'world',
    };
  }

  it("struct/CreateChargeRequest/create_instance", () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(CreateChargeRequest, payload);
    expect(instance).toBeDefined();
    expect(instance.cardToken).toBeDefined();
    expect(instance.amount).toBeDefined();
    expect(instance.currency).toBeDefined();
    expect(instance.reference).toBeDefined();
    expect(instance.idempotencyKey).toBeDefined();
  });

  it("struct/CreateChargeRequest/passes_validation", async () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(CreateChargeRequest, payload);
    const errors = await validate(instance);
    expect(errors.length).toBe(0);
  });

  it("struct/CreateChargeRequest/cardToken/required", async () => {
    const payload = buildValidPayload();
    delete payload.cardToken;
    const instance = plainToInstance(CreateChargeRequest, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/CreateChargeRequest/amount/required", async () => {
    const payload = buildValidPayload();
    delete payload.amount;
    const instance = plainToInstance(CreateChargeRequest, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/CreateChargeRequest/currency/required", async () => {
    const payload = buildValidPayload();
    delete payload.currency;
    const instance = plainToInstance(CreateChargeRequest, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/CreateChargeRequest/reference/required", async () => {
    const payload = buildValidPayload();
    delete payload.reference;
    const instance = plainToInstance(CreateChargeRequest, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/CreateChargeRequest/idempotencyKey/required", async () => {
    const payload = buildValidPayload();
    delete payload.idempotencyKey;
    const instance = plainToInstance(CreateChargeRequest, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/CreateChargeRequest/serialization_round_trip", () => {
    const instance = plainToInstance(CreateChargeRequest, buildValidPayload());
    const restored = plainToInstance(CreateChargeRequest, instanceToPlain(instance));
    expect(restored).toEqual(instance);
  });
});
