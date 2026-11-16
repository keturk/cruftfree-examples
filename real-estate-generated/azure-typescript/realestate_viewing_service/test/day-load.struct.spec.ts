import { validate } from 'class-validator';
import { instanceToPlain, plainToInstance } from 'class-transformer';
import { DayLoad } from '../src/dto/day-load.struct';

describe('DayLoad Struct', () => {
  function buildValidPayload(): Record<string, unknown> {
    return {
      day: 'world',
      viewings: 7,
    };
  }

  it("struct/DayLoad/create_instance", () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(DayLoad, payload);
    expect(instance).toBeDefined();
    expect(instance.day).toBeDefined();
    expect(instance.viewings).toBeDefined();
  });

  it("struct/DayLoad/passes_validation", async () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(DayLoad, payload);
    const errors = await validate(instance);
    expect(errors.length).toBe(0);
  });

  it("struct/DayLoad/day/required", async () => {
    const payload = buildValidPayload();
    delete payload.day;
    const instance = plainToInstance(DayLoad, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/DayLoad/viewings/required", async () => {
    const payload = buildValidPayload();
    delete payload.viewings;
    const instance = plainToInstance(DayLoad, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/DayLoad/serialization_round_trip", () => {
    const instance = plainToInstance(DayLoad, buildValidPayload());
    const restored = plainToInstance(DayLoad, instanceToPlain(instance));
    expect(restored).toEqual(instance);
  });
});
