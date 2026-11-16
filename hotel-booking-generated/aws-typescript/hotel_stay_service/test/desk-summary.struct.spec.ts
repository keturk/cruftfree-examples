import { validate } from 'class-validator';
import { instanceToPlain, plainToInstance } from 'class-transformer';
import { DeskSummary } from '../src/dto/desk-summary.struct';

describe('DeskSummary Struct', () => {
  function buildValidPayload(): Record<string, unknown> {
    return {
      arrivals: 100,
      departures: 100,
      inHouse: 42,
      roomsToClean: 7,
      occupancyPercent: 1,
    };
  }

  it("struct/DeskSummary/create_instance", () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(DeskSummary, payload);
    expect(instance).toBeDefined();
    expect(instance.arrivals).toBeDefined();
    expect(instance.departures).toBeDefined();
    expect(instance.inHouse).toBeDefined();
    expect(instance.roomsToClean).toBeDefined();
    expect(instance.occupancyPercent).toBeDefined();
  });

  it("struct/DeskSummary/passes_validation", async () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(DeskSummary, payload);
    const errors = await validate(instance);
    expect(errors.length).toBe(0);
  });

  it("struct/DeskSummary/arrivals/required", async () => {
    const payload = buildValidPayload();
    delete payload.arrivals;
    const instance = plainToInstance(DeskSummary, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/DeskSummary/departures/required", async () => {
    const payload = buildValidPayload();
    delete payload.departures;
    const instance = plainToInstance(DeskSummary, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/DeskSummary/inHouse/required", async () => {
    const payload = buildValidPayload();
    delete payload.inHouse;
    const instance = plainToInstance(DeskSummary, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/DeskSummary/roomsToClean/required", async () => {
    const payload = buildValidPayload();
    delete payload.roomsToClean;
    const instance = plainToInstance(DeskSummary, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/DeskSummary/occupancyPercent/required", async () => {
    const payload = buildValidPayload();
    delete payload.occupancyPercent;
    const instance = plainToInstance(DeskSummary, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/DeskSummary/serialization_round_trip", () => {
    const instance = plainToInstance(DeskSummary, buildValidPayload());
    const restored = plainToInstance(DeskSummary, instanceToPlain(instance));
    expect(restored).toEqual(instance);
  });
});
