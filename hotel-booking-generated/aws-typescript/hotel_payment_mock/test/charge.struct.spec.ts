import { validate } from 'class-validator';
import { instanceToPlain, plainToInstance } from 'class-transformer';
import { Charge } from '../src/dto/charge.struct';
import { ChargeStatus } from '../src/enums/charge-status.enum';

describe('Charge Struct', () => {
  function buildValidPayload(): Record<string, unknown> {
    return {
      id: 'test_string',
      status: ChargeStatus.Succeeded,
      declineReason: 'world',
    };
  }

  it("struct/Charge/create_instance", () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(Charge, payload);
    expect(instance).toBeDefined();
    expect(instance.id).toBeDefined();
    expect(instance.status).toBeDefined();
    expect(instance.declineReason).toBeDefined();
  });

  it("struct/Charge/passes_validation", async () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(Charge, payload);
    const errors = await validate(instance);
    expect(errors.length).toBe(0);
  });

  it("struct/Charge/id/required", async () => {
    const payload = buildValidPayload();
    delete payload.id;
    const instance = plainToInstance(Charge, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/Charge/status/required", async () => {
    const payload = buildValidPayload();
    delete payload.status;
    const instance = plainToInstance(Charge, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/Charge/serialization_round_trip", () => {
    const instance = plainToInstance(Charge, buildValidPayload());
    const restored = plainToInstance(Charge, instanceToPlain(instance));
    expect(restored).toEqual(instance);
  });
});
