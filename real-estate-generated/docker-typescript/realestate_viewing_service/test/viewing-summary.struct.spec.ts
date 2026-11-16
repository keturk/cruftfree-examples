import { validate } from 'class-validator';
import { instanceToPlain, plainToInstance } from 'class-transformer';
import { ViewingSummary } from '../src/dto/viewing-summary.struct';
import { DayLoad } from '../src/dto/day-load.struct';

describe('ViewingSummary Struct', () => {
  function buildValidPayload(): Record<string, unknown> {
    return {
      waitingForYou: 1,
      nextSevenDays: 7,
      ahead: [{day: 'world', viewings: 7} as DayLoad],
    };
  }

  it("struct/ViewingSummary/create_instance", () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(ViewingSummary, payload);
    expect(instance).toBeDefined();
    expect(instance.waitingForYou).toBeDefined();
    expect(instance.nextSevenDays).toBeDefined();
    expect(instance.ahead).toBeDefined();
  });

  it("struct/ViewingSummary/passes_validation", async () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(ViewingSummary, payload);
    const errors = await validate(instance);
    expect(errors.length).toBe(0);
  });

  it("struct/ViewingSummary/waitingForYou/required", async () => {
    const payload = buildValidPayload();
    delete payload.waitingForYou;
    const instance = plainToInstance(ViewingSummary, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/ViewingSummary/nextSevenDays/required", async () => {
    const payload = buildValidPayload();
    delete payload.nextSevenDays;
    const instance = plainToInstance(ViewingSummary, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/ViewingSummary/ahead/required", async () => {
    const payload = buildValidPayload();
    delete payload.ahead;
    const instance = plainToInstance(ViewingSummary, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/ViewingSummary/serialization_round_trip", () => {
    const instance = plainToInstance(ViewingSummary, buildValidPayload());
    const restored = plainToInstance(ViewingSummary, instanceToPlain(instance));
    expect(restored).toEqual(instance);
  });
});
