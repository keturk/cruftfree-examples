import { validate } from 'class-validator';
import { instanceToPlain, plainToInstance } from 'class-transformer';
import { Offer } from '../src/dto/offer.struct';

describe('Offer Struct', () => {
  function buildValidPayload(): Record<string, unknown> {
    return {
      roomTypeId: '7c9e6679-7425-40de-944b-e07fc1f90ae7',
      name: 'sample_text',
      summary: 'world',
      sleeps: 1,
      nightlyRate: '49.95',
      nights: 42,
      total: '49.95',
      left: 100,
    };
  }

  it("struct/Offer/create_instance", () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(Offer, payload);
    expect(instance).toBeDefined();
    expect(instance.roomTypeId).toBeDefined();
    expect(instance.name).toBeDefined();
    expect(instance.summary).toBeDefined();
    expect(instance.sleeps).toBeDefined();
    expect(instance.nightlyRate).toBeDefined();
    expect(instance.nights).toBeDefined();
    expect(instance.total).toBeDefined();
    expect(instance.left).toBeDefined();
  });

  it("struct/Offer/passes_validation", async () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(Offer, payload);
    const errors = await validate(instance);
    expect(errors.length).toBe(0);
  });

  it("struct/Offer/roomTypeId/required", async () => {
    const payload = buildValidPayload();
    delete payload.roomTypeId;
    const instance = plainToInstance(Offer, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/Offer/name/required", async () => {
    const payload = buildValidPayload();
    delete payload.name;
    const instance = plainToInstance(Offer, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/Offer/summary/required", async () => {
    const payload = buildValidPayload();
    delete payload.summary;
    const instance = plainToInstance(Offer, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/Offer/sleeps/required", async () => {
    const payload = buildValidPayload();
    delete payload.sleeps;
    const instance = plainToInstance(Offer, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/Offer/nightlyRate/required", async () => {
    const payload = buildValidPayload();
    delete payload.nightlyRate;
    const instance = plainToInstance(Offer, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/Offer/nights/required", async () => {
    const payload = buildValidPayload();
    delete payload.nights;
    const instance = plainToInstance(Offer, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/Offer/total/required", async () => {
    const payload = buildValidPayload();
    delete payload.total;
    const instance = plainToInstance(Offer, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/Offer/left/required", async () => {
    const payload = buildValidPayload();
    delete payload.left;
    const instance = plainToInstance(Offer, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/Offer/serialization_round_trip", () => {
    const instance = plainToInstance(Offer, buildValidPayload());
    const restored = plainToInstance(Offer, instanceToPlain(instance));
    expect(restored).toEqual(instance);
  });
});
