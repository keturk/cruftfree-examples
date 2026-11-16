import { validate } from 'class-validator';
import { instanceToPlain, plainToInstance } from 'class-transformer';
import { CalendarStay } from '../src/dto/calendar-stay.struct';

describe('CalendarStay Struct', () => {
  function buildValidPayload(): Record<string, unknown> {
    return {
      id: '7c9e6679-7425-40de-944b-e07fc1f90ae7',
      title: 'test_string',
      startsAt: new Date('2025-03-10T16:45:00Z'),
      endsAt: new Date('2025-03-10T16:45:00Z'),
    };
  }

  it("struct/CalendarStay/create_instance", () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(CalendarStay, payload);
    expect(instance).toBeDefined();
    expect(instance.id).toBeDefined();
    expect(instance.title).toBeDefined();
    expect(instance.startsAt).toBeDefined();
    expect(instance.endsAt).toBeDefined();
  });

  it("struct/CalendarStay/passes_validation", async () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(CalendarStay, payload);
    const errors = await validate(instance);
    expect(errors.length).toBe(0);
  });

  it("struct/CalendarStay/id/required", async () => {
    const payload = buildValidPayload();
    delete payload.id;
    const instance = plainToInstance(CalendarStay, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/CalendarStay/title/required", async () => {
    const payload = buildValidPayload();
    delete payload.title;
    const instance = plainToInstance(CalendarStay, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/CalendarStay/startsAt/required", async () => {
    const payload = buildValidPayload();
    delete payload.startsAt;
    const instance = plainToInstance(CalendarStay, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/CalendarStay/endsAt/required", async () => {
    const payload = buildValidPayload();
    delete payload.endsAt;
    const instance = plainToInstance(CalendarStay, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/CalendarStay/serialization_round_trip", () => {
    const instance = plainToInstance(CalendarStay, buildValidPayload());
    const restored = plainToInstance(CalendarStay, instanceToPlain(instance));
    expect(restored).toEqual(instance);
  });
});
