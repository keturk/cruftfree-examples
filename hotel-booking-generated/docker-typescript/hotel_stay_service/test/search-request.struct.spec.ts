import { validate } from 'class-validator';
import { instanceToPlain, plainToInstance } from 'class-transformer';
import { SearchRequest } from '../src/dto/search-request.struct';

describe('SearchRequest Struct', () => {
  function buildValidPayload(): Record<string, unknown> {
    return {
      arrival: '2025-03-10',
      departure: '2025-07-22',
      guests: 1,
    };
  }

  it("struct/SearchRequest/create_instance", () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(SearchRequest, payload);
    expect(instance).toBeDefined();
    expect(instance.arrival).toBeDefined();
    expect(instance.departure).toBeDefined();
    expect(instance.guests).toBeDefined();
  });

  it("struct/SearchRequest/passes_validation", async () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(SearchRequest, payload);
    const errors = await validate(instance);
    expect(errors.length).toBe(0);
  });

  it("struct/SearchRequest/arrival/required", async () => {
    const payload = buildValidPayload();
    delete payload.arrival;
    const instance = plainToInstance(SearchRequest, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/SearchRequest/departure/required", async () => {
    const payload = buildValidPayload();
    delete payload.departure;
    const instance = plainToInstance(SearchRequest, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/SearchRequest/guests/required", async () => {
    const payload = buildValidPayload();
    delete payload.guests;
    const instance = plainToInstance(SearchRequest, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/SearchRequest/serialization_round_trip", () => {
    const instance = plainToInstance(SearchRequest, buildValidPayload());
    const restored = plainToInstance(SearchRequest, instanceToPlain(instance));
    expect(restored).toEqual(instance);
  });
});
