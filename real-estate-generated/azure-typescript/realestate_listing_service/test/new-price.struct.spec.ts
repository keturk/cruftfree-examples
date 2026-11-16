import { validate } from 'class-validator';
import { instanceToPlain, plainToInstance } from 'class-transformer';
import { NewPrice } from '../src/dto/new-price.struct';

describe('NewPrice Struct', () => {
  function buildValidPayload(): Record<string, unknown> {
    return {
      listingId: '6ba7b810-9dad-11d1-80b4-00c04fd430c8',
      price: '149.00',
    };
  }

  it("struct/NewPrice/create_instance", () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(NewPrice, payload);
    expect(instance).toBeDefined();
    expect(instance.listingId).toBeDefined();
    expect(instance.price).toBeDefined();
  });

  it("struct/NewPrice/passes_validation", async () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(NewPrice, payload);
    const errors = await validate(instance);
    expect(errors.length).toBe(0);
  });

  it("struct/NewPrice/listingId/required", async () => {
    const payload = buildValidPayload();
    delete payload.listingId;
    const instance = plainToInstance(NewPrice, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/NewPrice/price/required", async () => {
    const payload = buildValidPayload();
    delete payload.price;
    const instance = plainToInstance(NewPrice, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/NewPrice/serialization_round_trip", () => {
    const instance = plainToInstance(NewPrice, buildValidPayload());
    const restored = plainToInstance(NewPrice, instanceToPlain(instance));
    expect(restored).toEqual(instance);
  });
});
