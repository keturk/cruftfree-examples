import { validate } from 'class-validator';
import { instanceToPlain, plainToInstance } from 'class-transformer';
import { GeoPoint } from '../src/dto/geo-point.struct';

describe('GeoPoint Struct', () => {
  function buildValidPayload(): Record<string, unknown> {
    return {
      latitude: 99.9,
      longitude: 99.9,
      accuracyM: 99.9,
    };
  }

  it("struct/GeoPoint/create_instance", () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(GeoPoint, payload);
    expect(instance).toBeDefined();
    expect(instance.latitude).toBeDefined();
    expect(instance.longitude).toBeDefined();
    expect(instance.accuracyM).toBeDefined();
  });

  it("struct/GeoPoint/passes_validation", async () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(GeoPoint, payload);
    const errors = await validate(instance);
    expect(errors.length).toBe(0);
  });

  it("struct/GeoPoint/latitude/required", async () => {
    const payload = buildValidPayload();
    delete payload.latitude;
    const instance = plainToInstance(GeoPoint, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/GeoPoint/longitude/required", async () => {
    const payload = buildValidPayload();
    delete payload.longitude;
    const instance = plainToInstance(GeoPoint, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/GeoPoint/serialization_round_trip", () => {
    const instance = plainToInstance(GeoPoint, buildValidPayload());
    const restored = plainToInstance(GeoPoint, instanceToPlain(instance));
    expect(restored).toEqual(instance);
  });
});
