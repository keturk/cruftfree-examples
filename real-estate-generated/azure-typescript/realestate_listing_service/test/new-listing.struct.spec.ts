import { validate } from 'class-validator';
import { instanceToPlain, plainToInstance } from 'class-transformer';
import { NewListing } from '../src/dto/new-listing.struct';
import { PropertyKind } from '../src/enums/property-kind.enum';

describe('NewListing Struct', () => {
  function buildValidPayload(): Record<string, unknown> {
    return {
      title: 'hello',
      neighbourhoodId: '7c9e6679-7425-40de-944b-e07fc1f90ae7',
      kind: PropertyKind.House,
      price: '9.99',
      bedrooms: 1,
      bathrooms: 100,
      areaSqm: 42,
      summary: 'Lorem ipsum dolor sit amet',
    };
  }

  it("struct/NewListing/create_instance", () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(NewListing, payload);
    expect(instance).toBeDefined();
    expect(instance.title).toBeDefined();
    expect(instance.neighbourhoodId).toBeDefined();
    expect(instance.kind).toBeDefined();
    expect(instance.price).toBeDefined();
    expect(instance.bedrooms).toBeDefined();
    expect(instance.bathrooms).toBeDefined();
    expect(instance.areaSqm).toBeDefined();
    expect(instance.summary).toBeDefined();
  });

  it("struct/NewListing/passes_validation", async () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(NewListing, payload);
    const errors = await validate(instance);
    expect(errors.length).toBe(0);
  });

  it("struct/NewListing/title/required", async () => {
    const payload = buildValidPayload();
    delete payload.title;
    const instance = plainToInstance(NewListing, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/NewListing/neighbourhoodId/required", async () => {
    const payload = buildValidPayload();
    delete payload.neighbourhoodId;
    const instance = plainToInstance(NewListing, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/NewListing/kind/required", async () => {
    const payload = buildValidPayload();
    delete payload.kind;
    const instance = plainToInstance(NewListing, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/NewListing/price/required", async () => {
    const payload = buildValidPayload();
    delete payload.price;
    const instance = plainToInstance(NewListing, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/NewListing/bedrooms/required", async () => {
    const payload = buildValidPayload();
    delete payload.bedrooms;
    const instance = plainToInstance(NewListing, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/NewListing/bathrooms/required", async () => {
    const payload = buildValidPayload();
    delete payload.bathrooms;
    const instance = plainToInstance(NewListing, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/NewListing/areaSqm/required", async () => {
    const payload = buildValidPayload();
    delete payload.areaSqm;
    const instance = plainToInstance(NewListing, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/NewListing/summary/required", async () => {
    const payload = buildValidPayload();
    delete payload.summary;
    const instance = plainToInstance(NewListing, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/NewListing/serialization_round_trip", () => {
    const instance = plainToInstance(NewListing, buildValidPayload());
    const restored = plainToInstance(NewListing, instanceToPlain(instance));
    expect(restored).toEqual(instance);
  });
});
