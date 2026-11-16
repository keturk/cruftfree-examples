import { validate } from 'class-validator';
import { instanceToPlain, plainToInstance } from 'class-transformer';
import { OccupancyPoint } from '../src/dto/occupancy-point.struct';

describe('OccupancyPoint Struct', () => {
  function buildValidPayload(): Record<string, unknown> {
    return {
      night: 'world',
      sold: 7,
      left: 7,
    };
  }

  it("struct/OccupancyPoint/create_instance", () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(OccupancyPoint, payload);
    expect(instance).toBeDefined();
    expect(instance.night).toBeDefined();
    expect(instance.sold).toBeDefined();
    expect(instance.left).toBeDefined();
  });

  it("struct/OccupancyPoint/passes_validation", async () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(OccupancyPoint, payload);
    const errors = await validate(instance);
    expect(errors.length).toBe(0);
  });

  it("struct/OccupancyPoint/night/required", async () => {
    const payload = buildValidPayload();
    delete payload.night;
    const instance = plainToInstance(OccupancyPoint, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/OccupancyPoint/sold/required", async () => {
    const payload = buildValidPayload();
    delete payload.sold;
    const instance = plainToInstance(OccupancyPoint, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/OccupancyPoint/left/required", async () => {
    const payload = buildValidPayload();
    delete payload.left;
    const instance = plainToInstance(OccupancyPoint, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/OccupancyPoint/serialization_round_trip", () => {
    const instance = plainToInstance(OccupancyPoint, buildValidPayload());
    const restored = plainToInstance(OccupancyPoint, instanceToPlain(instance));
    expect(restored).toEqual(instance);
  });
});
