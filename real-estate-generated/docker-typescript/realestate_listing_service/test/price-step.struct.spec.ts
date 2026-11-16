import { validate } from 'class-validator';
import { instanceToPlain, plainToInstance } from 'class-transformer';
import { PriceStep } from '../src/dto/price-step.struct';

describe('PriceStep Struct', () => {
  function buildValidPayload(): Record<string, unknown> {
    return {
      oldPrice: '49.95',
      newPrice: '9.99',
      at: new Date('2025-03-10T16:45:00Z'),
    };
  }

  it("struct/PriceStep/create_instance", () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(PriceStep, payload);
    expect(instance).toBeDefined();
    expect(instance.oldPrice).toBeDefined();
    expect(instance.newPrice).toBeDefined();
    expect(instance.at).toBeDefined();
  });

  it("struct/PriceStep/passes_validation", async () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(PriceStep, payload);
    const errors = await validate(instance);
    expect(errors.length).toBe(0);
  });

  it("struct/PriceStep/oldPrice/required", async () => {
    const payload = buildValidPayload();
    delete payload.oldPrice;
    const instance = plainToInstance(PriceStep, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/PriceStep/newPrice/required", async () => {
    const payload = buildValidPayload();
    delete payload.newPrice;
    const instance = plainToInstance(PriceStep, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/PriceStep/at/required", async () => {
    const payload = buildValidPayload();
    delete payload.at;
    const instance = plainToInstance(PriceStep, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/PriceStep/serialization_round_trip", () => {
    const instance = plainToInstance(PriceStep, buildValidPayload());
    const restored = plainToInstance(PriceStep, instanceToPlain(instance));
    expect(restored).toEqual(instance);
  });
});
