import { validate } from 'class-validator';
import { instanceToPlain, plainToInstance } from 'class-transformer';
import { ListingNotice } from '../src/dto/listing-notice.struct';

describe('ListingNotice Struct', () => {
  function buildValidPayload(): Record<string, unknown> {
    return {
      listingId: '6ba7b810-9dad-11d1-80b4-00c04fd430c8',
    };
  }

  it("struct/ListingNotice/create_instance", () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(ListingNotice, payload);
    expect(instance).toBeDefined();
    expect(instance.listingId).toBeDefined();
  });

  it("struct/ListingNotice/passes_validation", async () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(ListingNotice, payload);
    const errors = await validate(instance);
    expect(errors.length).toBe(0);
  });

  it("struct/ListingNotice/listingId/required", async () => {
    const payload = buildValidPayload();
    delete payload.listingId;
    const instance = plainToInstance(ListingNotice, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/ListingNotice/serialization_round_trip", () => {
    const instance = plainToInstance(ListingNotice, buildValidPayload());
    const restored = plainToInstance(ListingNotice, instanceToPlain(instance));
    expect(restored).toEqual(instance);
  });
});
