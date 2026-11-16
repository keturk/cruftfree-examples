import { validate } from 'class-validator';
import { instanceToPlain, plainToInstance } from 'class-transformer';
import { MakeOffer } from '../src/dto/make-offer.struct';
import { Financing } from '../src/enums/financing.enum';

describe('MakeOffer Struct', () => {
  function buildValidPayload(): Record<string, unknown> {
    return {
      listingId: 'f47ac10b-58cc-4372-a567-0e02b2c3d479',
      amount: '9.99',
      financing: Financing.Cash,
    };
  }

  it("struct/MakeOffer/create_instance", () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(MakeOffer, payload);
    expect(instance).toBeDefined();
    expect(instance.listingId).toBeDefined();
    expect(instance.amount).toBeDefined();
    expect(instance.financing).toBeDefined();
  });

  it("struct/MakeOffer/passes_validation", async () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(MakeOffer, payload);
    const errors = await validate(instance);
    expect(errors.length).toBe(0);
  });

  it("struct/MakeOffer/listingId/required", async () => {
    const payload = buildValidPayload();
    delete payload.listingId;
    const instance = plainToInstance(MakeOffer, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/MakeOffer/amount/required", async () => {
    const payload = buildValidPayload();
    delete payload.amount;
    const instance = plainToInstance(MakeOffer, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/MakeOffer/financing/required", async () => {
    const payload = buildValidPayload();
    delete payload.financing;
    const instance = plainToInstance(MakeOffer, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/MakeOffer/serialization_round_trip", () => {
    const instance = plainToInstance(MakeOffer, buildValidPayload());
    const restored = plainToInstance(MakeOffer, instanceToPlain(instance));
    expect(restored).toEqual(instance);
  });
});
