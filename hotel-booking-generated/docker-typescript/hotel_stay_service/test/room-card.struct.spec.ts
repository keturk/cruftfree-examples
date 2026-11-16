import { validate } from 'class-validator';
import { instanceToPlain, plainToInstance } from 'class-transformer';
import { RoomCard } from '../src/dto/room-card.struct';
import { RoomCondition } from '../src/enums/room-condition.enum';

describe('RoomCard Struct', () => {
  function buildValidPayload(): Record<string, unknown> {
    return {
      id: '6ba7b810-9dad-11d1-80b4-00c04fd430c8',
      number: 'foo_bar',
      roomTypeName: 'world',
      floor: 256,
      condition: RoomCondition.Ready,
    };
  }

  it("struct/RoomCard/create_instance", () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(RoomCard, payload);
    expect(instance).toBeDefined();
    expect(instance.id).toBeDefined();
    expect(instance.number).toBeDefined();
    expect(instance.roomTypeName).toBeDefined();
    expect(instance.floor).toBeDefined();
    expect(instance.condition).toBeDefined();
  });

  it("struct/RoomCard/passes_validation", async () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(RoomCard, payload);
    const errors = await validate(instance);
    expect(errors.length).toBe(0);
  });

  it("struct/RoomCard/id/required", async () => {
    const payload = buildValidPayload();
    delete payload.id;
    const instance = plainToInstance(RoomCard, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/RoomCard/number/required", async () => {
    const payload = buildValidPayload();
    delete payload.number;
    const instance = plainToInstance(RoomCard, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/RoomCard/roomTypeName/required", async () => {
    const payload = buildValidPayload();
    delete payload.roomTypeName;
    const instance = plainToInstance(RoomCard, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/RoomCard/floor/required", async () => {
    const payload = buildValidPayload();
    delete payload.floor;
    const instance = plainToInstance(RoomCard, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/RoomCard/condition/required", async () => {
    const payload = buildValidPayload();
    delete payload.condition;
    const instance = plainToInstance(RoomCard, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/RoomCard/serialization_round_trip", () => {
    const instance = plainToInstance(RoomCard, buildValidPayload());
    const restored = plainToInstance(RoomCard, instanceToPlain(instance));
    expect(restored).toEqual(instance);
  });
});
