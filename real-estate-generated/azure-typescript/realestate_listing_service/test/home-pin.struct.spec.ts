import { validate } from 'class-validator';
import { instanceToPlain, plainToInstance } from 'class-transformer';
import { HomePin } from '../src/dto/home-pin.struct';
import { GeoPoint } from '../src/dto/geo-point.struct';

describe('HomePin Struct', () => {
  function buildValidPayload(): Record<string, unknown> {
    return {
      id: 'f47ac10b-58cc-4372-a567-0e02b2c3d479',
      title: 'hello',
      point: {latitude: 99.9, longitude: 99.9, accuracyM: 99.9} as GeoPoint,
    };
  }

  it("struct/HomePin/create_instance", () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(HomePin, payload);
    expect(instance).toBeDefined();
    expect(instance.id).toBeDefined();
    expect(instance.title).toBeDefined();
    expect(instance.point).toBeDefined();
  });

  it("struct/HomePin/passes_validation", async () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(HomePin, payload);
    const errors = await validate(instance);
    expect(errors.length).toBe(0);
  });

  it("struct/HomePin/id/required", async () => {
    const payload = buildValidPayload();
    delete payload.id;
    const instance = plainToInstance(HomePin, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/HomePin/title/required", async () => {
    const payload = buildValidPayload();
    delete payload.title;
    const instance = plainToInstance(HomePin, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/HomePin/point/required", async () => {
    const payload = buildValidPayload();
    delete payload.point;
    const instance = plainToInstance(HomePin, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/HomePin/serialization_round_trip", () => {
    const instance = plainToInstance(HomePin, buildValidPayload());
    const restored = plainToInstance(HomePin, instanceToPlain(instance));
    expect(restored).toEqual(instance);
  });
});
