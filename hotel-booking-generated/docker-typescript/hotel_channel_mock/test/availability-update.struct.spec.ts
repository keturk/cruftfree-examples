import { validate } from 'class-validator';
import { instanceToPlain, plainToInstance } from 'class-transformer';
import { AvailabilityUpdate } from '../src/dto/availability-update.struct';

describe('AvailabilityUpdate Struct', () => {
  function buildValidPayload(): Record<string, unknown> {
    return {
      roomType: 'foo_bar',
      night: '2024-11-05',
      left: 7,
      nightlyRate: '49.95',
    };
  }

  it("struct/AvailabilityUpdate/create_instance", () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(AvailabilityUpdate, payload);
    expect(instance).toBeDefined();
    expect(instance.roomType).toBeDefined();
    expect(instance.night).toBeDefined();
    expect(instance.left).toBeDefined();
    expect(instance.nightlyRate).toBeDefined();
  });

  it("struct/AvailabilityUpdate/passes_validation", async () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(AvailabilityUpdate, payload);
    const errors = await validate(instance);
    expect(errors.length).toBe(0);
  });

  it("struct/AvailabilityUpdate/roomType/required", async () => {
    const payload = buildValidPayload();
    delete payload.roomType;
    const instance = plainToInstance(AvailabilityUpdate, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/AvailabilityUpdate/night/required", async () => {
    const payload = buildValidPayload();
    delete payload.night;
    const instance = plainToInstance(AvailabilityUpdate, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/AvailabilityUpdate/left/required", async () => {
    const payload = buildValidPayload();
    delete payload.left;
    const instance = plainToInstance(AvailabilityUpdate, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/AvailabilityUpdate/nightlyRate/required", async () => {
    const payload = buildValidPayload();
    delete payload.nightlyRate;
    const instance = plainToInstance(AvailabilityUpdate, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/AvailabilityUpdate/serialization_round_trip", () => {
    const instance = plainToInstance(AvailabilityUpdate, buildValidPayload());
    const restored = plainToInstance(AvailabilityUpdate, instanceToPlain(instance));
    expect(restored).toEqual(instance);
  });
});
