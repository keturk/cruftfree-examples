import { validate } from 'class-validator';
import { instanceToPlain, plainToInstance } from 'class-transformer';
import { RoomTypeCard } from '../src/dto/room-type-card.struct';

describe('RoomTypeCard Struct', () => {
  function buildValidPayload(): Record<string, unknown> {
    return {
      id: 'f47ac10b-58cc-4372-a567-0e02b2c3d479',
      name: 'foo_bar',
      summary: 'foo_bar',
      description: 'foo_bar',
      sleeps: 42,
      nightlyRate: '4.50',
    };
  }

  it("struct/RoomTypeCard/create_instance", () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(RoomTypeCard, payload);
    expect(instance).toBeDefined();
    expect(instance.id).toBeDefined();
    expect(instance.name).toBeDefined();
    expect(instance.summary).toBeDefined();
    expect(instance.description).toBeDefined();
    expect(instance.sleeps).toBeDefined();
    expect(instance.nightlyRate).toBeDefined();
  });

  it("struct/RoomTypeCard/passes_validation", async () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(RoomTypeCard, payload);
    const errors = await validate(instance);
    expect(errors.length).toBe(0);
  });

  it("struct/RoomTypeCard/id/required", async () => {
    const payload = buildValidPayload();
    delete payload.id;
    const instance = plainToInstance(RoomTypeCard, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/RoomTypeCard/name/required", async () => {
    const payload = buildValidPayload();
    delete payload.name;
    const instance = plainToInstance(RoomTypeCard, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/RoomTypeCard/summary/required", async () => {
    const payload = buildValidPayload();
    delete payload.summary;
    const instance = plainToInstance(RoomTypeCard, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/RoomTypeCard/description/required", async () => {
    const payload = buildValidPayload();
    delete payload.description;
    const instance = plainToInstance(RoomTypeCard, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/RoomTypeCard/sleeps/required", async () => {
    const payload = buildValidPayload();
    delete payload.sleeps;
    const instance = plainToInstance(RoomTypeCard, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/RoomTypeCard/nightlyRate/required", async () => {
    const payload = buildValidPayload();
    delete payload.nightlyRate;
    const instance = plainToInstance(RoomTypeCard, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/RoomTypeCard/serialization_round_trip", () => {
    const instance = plainToInstance(RoomTypeCard, buildValidPayload());
    const restored = plainToInstance(RoomTypeCard, instanceToPlain(instance));
    expect(restored).toEqual(instance);
  });
});
