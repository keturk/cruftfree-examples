import { validate } from 'class-validator';
import { instanceToPlain, plainToInstance } from 'class-transformer';
import { AvailabilityPush } from '../src/dto/availability-push.struct';
import { AvailabilityUpdate } from '../src/dto/availability-update.struct';

describe('AvailabilityPush Struct', () => {
  function buildValidPayload(): Record<string, unknown> {
    return {
      propertyCode: 'test_string',
      nights: [{roomType: 'foo_bar', night: '2024-11-05', left: 7, nightlyRate: '49.95'} as AvailabilityUpdate],
    };
  }

  it("struct/AvailabilityPush/create_instance", () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(AvailabilityPush, payload);
    expect(instance).toBeDefined();
    expect(instance.propertyCode).toBeDefined();
    expect(instance.nights).toBeDefined();
  });

  it("struct/AvailabilityPush/passes_validation", async () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(AvailabilityPush, payload);
    const errors = await validate(instance);
    expect(errors.length).toBe(0);
  });

  it("struct/AvailabilityPush/propertyCode/required", async () => {
    const payload = buildValidPayload();
    delete payload.propertyCode;
    const instance = plainToInstance(AvailabilityPush, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/AvailabilityPush/nights/required", async () => {
    const payload = buildValidPayload();
    delete payload.nights;
    const instance = plainToInstance(AvailabilityPush, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/AvailabilityPush/serialization_round_trip", () => {
    const instance = plainToInstance(AvailabilityPush, buildValidPayload());
    const restored = plainToInstance(AvailabilityPush, instanceToPlain(instance));
    expect(restored).toEqual(instance);
  });
});
