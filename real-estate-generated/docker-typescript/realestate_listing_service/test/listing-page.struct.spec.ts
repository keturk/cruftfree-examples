import { validate } from 'class-validator';
import { instanceToPlain, plainToInstance } from 'class-transformer';
import { ListingPage } from '../src/dto/listing-page.struct';
import { GeoPoint } from '../src/dto/geo-point.struct';
import { ListingCard } from '../src/dto/listing-card.struct';
import { ListingStatus } from '../src/enums/listing-status.enum';
import { PriceStep } from '../src/dto/price-step.struct';
import { PropertyKind } from '../src/enums/property-kind.enum';

describe('ListingPage Struct', () => {
  function buildValidPayload(): Record<string, unknown> {
    return {
      home: {id: 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', title: 'foo_bar', neighbourhoodName: 'foo_bar', city: 'sample_text', kind: PropertyKind.House, price: '9.99', bedrooms: 1, bathrooms: 1, areaSqm: 256, status: ListingStatus.Draft} as ListingCard,
      summary: 'Sample paragraph text for testing',
      agentName: 'test_string',
      point: {latitude: 99.9, longitude: 99.9, accuracyM: 99.9} as GeoPoint,
      priceHistory: [{oldPrice: '49.95', newPrice: '9.99', at: new Date('2025-03-10T16:45:00Z')} as PriceStep],
    };
  }

  it("struct/ListingPage/create_instance", () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(ListingPage, payload);
    expect(instance).toBeDefined();
    expect(instance.home).toBeDefined();
    expect(instance.summary).toBeDefined();
    expect(instance.agentName).toBeDefined();
    expect(instance.point).toBeDefined();
    expect(instance.priceHistory).toBeDefined();
  });

  it("struct/ListingPage/passes_validation", async () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(ListingPage, payload);
    const errors = await validate(instance);
    expect(errors.length).toBe(0);
  });

  it("struct/ListingPage/home/required", async () => {
    const payload = buildValidPayload();
    delete payload.home;
    const instance = plainToInstance(ListingPage, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/ListingPage/summary/required", async () => {
    const payload = buildValidPayload();
    delete payload.summary;
    const instance = plainToInstance(ListingPage, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/ListingPage/agentName/required", async () => {
    const payload = buildValidPayload();
    delete payload.agentName;
    const instance = plainToInstance(ListingPage, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/ListingPage/point/required", async () => {
    const payload = buildValidPayload();
    delete payload.point;
    const instance = plainToInstance(ListingPage, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/ListingPage/priceHistory/required", async () => {
    const payload = buildValidPayload();
    delete payload.priceHistory;
    const instance = plainToInstance(ListingPage, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/ListingPage/serialization_round_trip", () => {
    const instance = plainToInstance(ListingPage, buildValidPayload());
    const restored = plainToInstance(ListingPage, instanceToPlain(instance));
    expect(restored).toEqual(instance);
  });
});
