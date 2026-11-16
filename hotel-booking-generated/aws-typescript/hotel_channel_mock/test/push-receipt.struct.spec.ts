import { validate } from 'class-validator';
import { instanceToPlain, plainToInstance } from 'class-transformer';
import { PushReceipt } from '../src/dto/push-receipt.struct';

describe('PushReceipt Struct', () => {
  function buildValidPayload(): Record<string, unknown> {
    return {
      accepted: 7,
    };
  }

  it("struct/PushReceipt/create_instance", () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(PushReceipt, payload);
    expect(instance).toBeDefined();
    expect(instance.accepted).toBeDefined();
  });

  it("struct/PushReceipt/passes_validation", async () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(PushReceipt, payload);
    const errors = await validate(instance);
    expect(errors.length).toBe(0);
  });

  it("struct/PushReceipt/accepted/required", async () => {
    const payload = buildValidPayload();
    delete payload.accepted;
    const instance = plainToInstance(PushReceipt, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/PushReceipt/serialization_round_trip", () => {
    const instance = plainToInstance(PushReceipt, buildValidPayload());
    const restored = plainToInstance(PushReceipt, instanceToPlain(instance));
    expect(restored).toEqual(instance);
  });
});
