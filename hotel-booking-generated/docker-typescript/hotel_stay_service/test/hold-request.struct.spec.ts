import { validate } from 'class-validator';
import { instanceToPlain, plainToInstance } from 'class-transformer';
import { HoldRequest } from '../src/dto/hold-request.struct';

describe('HoldRequest Struct', () => {
  function buildValidPayload(): Record<string, unknown> {
    return {
      roomTypeId: 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
      arrival: '2025-01-15',
      departure: '2024-06-20',
      guests: 7,
    };
  }

  it("struct/HoldRequest/create_instance", () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(HoldRequest, payload);
    expect(instance).toBeDefined();
    expect(instance.roomTypeId).toBeDefined();
    expect(instance.arrival).toBeDefined();
    expect(instance.departure).toBeDefined();
    expect(instance.guests).toBeDefined();
  });

  it("struct/HoldRequest/passes_validation", async () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(HoldRequest, payload);
    const errors = await validate(instance);
    expect(errors.length).toBe(0);
  });

  it("struct/HoldRequest/roomTypeId/required", async () => {
    const payload = buildValidPayload();
    delete payload.roomTypeId;
    const instance = plainToInstance(HoldRequest, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/HoldRequest/arrival/required", async () => {
    const payload = buildValidPayload();
    delete payload.arrival;
    const instance = plainToInstance(HoldRequest, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/HoldRequest/departure/required", async () => {
    const payload = buildValidPayload();
    delete payload.departure;
    const instance = plainToInstance(HoldRequest, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/HoldRequest/guests/required", async () => {
    const payload = buildValidPayload();
    delete payload.guests;
    const instance = plainToInstance(HoldRequest, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/HoldRequest/serialization_round_trip", () => {
    const instance = plainToInstance(HoldRequest, buildValidPayload());
    const restored = plainToInstance(HoldRequest, instanceToPlain(instance));
    expect(restored).toEqual(instance);
  });
});
