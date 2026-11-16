import { validate } from 'class-validator';
import { instanceToPlain, plainToInstance } from 'class-transformer';
import { Delivery } from '../src/dto/delivery.struct';
import { DeliveryStatus } from '../src/enums/delivery-status.enum';

describe('Delivery Struct', () => {
  function buildValidPayload(): Record<string, unknown> {
    return {
      id: 'sample_text',
      status: DeliveryStatus.Delivered,
    };
  }

  it("struct/Delivery/create_instance", () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(Delivery, payload);
    expect(instance).toBeDefined();
    expect(instance.id).toBeDefined();
    expect(instance.status).toBeDefined();
  });

  it("struct/Delivery/passes_validation", async () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(Delivery, payload);
    const errors = await validate(instance);
    expect(errors.length).toBe(0);
  });

  it("struct/Delivery/id/required", async () => {
    const payload = buildValidPayload();
    delete payload.id;
    const instance = plainToInstance(Delivery, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/Delivery/status/required", async () => {
    const payload = buildValidPayload();
    delete payload.status;
    const instance = plainToInstance(Delivery, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/Delivery/serialization_round_trip", () => {
    const instance = plainToInstance(Delivery, buildValidPayload());
    const restored = plainToInstance(Delivery, instanceToPlain(instance));
    expect(restored).toEqual(instance);
  });
});
