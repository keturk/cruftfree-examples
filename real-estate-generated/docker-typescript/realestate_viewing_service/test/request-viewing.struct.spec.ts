import { validate } from 'class-validator';
import { instanceToPlain, plainToInstance } from 'class-transformer';
import { RequestViewing } from '../src/dto/request-viewing.struct';

describe('RequestViewing Struct', () => {
  function buildValidPayload(): Record<string, unknown> {
    return {
      listingId: 'f47ac10b-58cc-4372-a567-0e02b2c3d479',
      startsAt: new Date('2024-11-05T09:15:00Z'),
      note: 'foo_bar',
    };
  }

  it("struct/RequestViewing/create_instance", () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(RequestViewing, payload);
    expect(instance).toBeDefined();
    expect(instance.listingId).toBeDefined();
    expect(instance.startsAt).toBeDefined();
    expect(instance.note).toBeDefined();
  });

  it("struct/RequestViewing/passes_validation", async () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(RequestViewing, payload);
    const errors = await validate(instance);
    expect(errors.length).toBe(0);
  });

  it("struct/RequestViewing/listingId/required", async () => {
    const payload = buildValidPayload();
    delete payload.listingId;
    const instance = plainToInstance(RequestViewing, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/RequestViewing/startsAt/required", async () => {
    const payload = buildValidPayload();
    delete payload.startsAt;
    const instance = plainToInstance(RequestViewing, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/RequestViewing/serialization_round_trip", () => {
    const instance = plainToInstance(RequestViewing, buildValidPayload());
    const restored = plainToInstance(RequestViewing, instanceToPlain(instance));
    expect(restored).toEqual(instance);
  });
});
