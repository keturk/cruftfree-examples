import { validate } from 'class-validator';
import { instanceToPlain, plainToInstance } from 'class-transformer';
import { ListingCard } from '../src/dto/listing-card.struct';
import { ListingStatus } from '../src/enums/listing-status.enum';
import { PropertyKind } from '../src/enums/property-kind.enum';

describe('ListingCard Struct', () => {
  function buildValidPayload(): Record<string, unknown> {
    return {
      id: 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
      title: 'foo_bar',
      neighbourhoodName: 'foo_bar',
      city: 'sample_text',
      kind: PropertyKind.House,
      price: '9.99',
      bedrooms: 1,
      bathrooms: 1,
      areaSqm: 256,
      status: ListingStatus.Draft,
    };
  }

  it("struct/ListingCard/create_instance", () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(ListingCard, payload);
    expect(instance).toBeDefined();
    expect(instance.id).toBeDefined();
    expect(instance.title).toBeDefined();
    expect(instance.neighbourhoodName).toBeDefined();
    expect(instance.city).toBeDefined();
    expect(instance.kind).toBeDefined();
    expect(instance.price).toBeDefined();
    expect(instance.bedrooms).toBeDefined();
    expect(instance.bathrooms).toBeDefined();
    expect(instance.areaSqm).toBeDefined();
    expect(instance.status).toBeDefined();
  });

  it("struct/ListingCard/passes_validation", async () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(ListingCard, payload);
    const errors = await validate(instance);
    expect(errors.length).toBe(0);
  });

  it("struct/ListingCard/id/required", async () => {
    const payload = buildValidPayload();
    delete payload.id;
    const instance = plainToInstance(ListingCard, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/ListingCard/title/required", async () => {
    const payload = buildValidPayload();
    delete payload.title;
    const instance = plainToInstance(ListingCard, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/ListingCard/neighbourhoodName/required", async () => {
    const payload = buildValidPayload();
    delete payload.neighbourhoodName;
    const instance = plainToInstance(ListingCard, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/ListingCard/city/required", async () => {
    const payload = buildValidPayload();
    delete payload.city;
    const instance = plainToInstance(ListingCard, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/ListingCard/kind/required", async () => {
    const payload = buildValidPayload();
    delete payload.kind;
    const instance = plainToInstance(ListingCard, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/ListingCard/price/required", async () => {
    const payload = buildValidPayload();
    delete payload.price;
    const instance = plainToInstance(ListingCard, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/ListingCard/bedrooms/required", async () => {
    const payload = buildValidPayload();
    delete payload.bedrooms;
    const instance = plainToInstance(ListingCard, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/ListingCard/bathrooms/required", async () => {
    const payload = buildValidPayload();
    delete payload.bathrooms;
    const instance = plainToInstance(ListingCard, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/ListingCard/areaSqm/required", async () => {
    const payload = buildValidPayload();
    delete payload.areaSqm;
    const instance = plainToInstance(ListingCard, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/ListingCard/status/required", async () => {
    const payload = buildValidPayload();
    delete payload.status;
    const instance = plainToInstance(ListingCard, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/ListingCard/serialization_round_trip", () => {
    const instance = plainToInstance(ListingCard, buildValidPayload());
    const restored = plainToInstance(ListingCard, instanceToPlain(instance));
    expect(restored).toEqual(instance);
  });
});
