import { MetadataStorage } from '@mikro-orm/core';
import { Listing } from '../src/realestate_listing_service/entities/listing_db/listing.entity';
import { PropertyKind } from '../src/enums/property-kind.enum';
import { ListingStatus } from '../src/enums/listing-status.enum';

/** The decorator metadata of a mapped property, declared on the entity or a class it extends. */
function propertyMetadata(name: string): { length?: number; nullable?: boolean } {
  let target: unknown = Listing;
  while (typeof target === 'function' && target !== Function.prototype) {
    const meta = MetadataStorage.getMetadataFromDecorator(target as new () => object);
    const properties = meta.properties as Record<string, { length?: number; nullable?: boolean } | undefined>;
    const property = properties[name];
    if (property !== undefined) {
      return property;
    }
    target = Object.getPrototypeOf(target);
  }
  throw new Error(`Listing maps no property '${name}'.`);
}

describe('Listing Entity', () => {
  it("entity_model/listingDb/Listing/create_instance", () => {
    const entity = new Listing();
    expect(entity).toBeDefined();
  });

  it("entity_model/listingDb/Listing/field_assignment", () => {
    const entity = new Listing();
    const titleVal = 'foo_bar';
    const neighbourhoodNameVal = 'sample_text';
    const kindVal = PropertyKind.House;
    const priceVal = '49.95';
    const bedroomsVal = 42;
    const bathroomsVal = 42;
    const areaSqmVal = 7;
    const statusVal = ListingStatus.Draft;
    const agentNameVal = 'sample_text';
    const publishedAtVal = new Date('2025-01-15T12:00:00Z');
    const summaryVal = 'Test content body with details';
    const cityVal = 'foo_bar';
    const latitudeVal = 2.718;
    const longitudeVal = 0.5;
    const agentEmailVal = 'hello@world.com';
    entity.title = titleVal;
    entity.neighbourhoodName = neighbourhoodNameVal;
    entity.kind = kindVal;
    entity.price = priceVal;
    entity.bedrooms = bedroomsVal;
    entity.bathrooms = bathroomsVal;
    entity.areaSqm = areaSqmVal;
    entity.status = statusVal;
    entity.agentName = agentNameVal;
    entity.publishedAt = publishedAtVal;
    entity.summary = summaryVal;
    entity.city = cityVal;
    entity.latitude = latitudeVal;
    entity.longitude = longitudeVal;
    entity.agentEmail = agentEmailVal;
    expect(entity.title).toBe(titleVal);
    expect(entity.neighbourhoodName).toBe(neighbourhoodNameVal);
    expect(entity.kind).toBe(kindVal);
    expect(entity.price).toBe(priceVal);
    expect(entity.bedrooms).toBe(bedroomsVal);
    expect(entity.bathrooms).toBe(bathroomsVal);
    expect(entity.areaSqm).toBe(areaSqmVal);
    expect(entity.status).toBe(statusVal);
    expect(entity.agentName).toBe(agentNameVal);
    expect(entity.publishedAt).toEqual(publishedAtVal);
    expect(entity.summary).toBe(summaryVal);
    expect(entity.city).toBe(cityVal);
    expect(entity.latitude).toBe(latitudeVal);
    expect(entity.longitude).toBe(longitudeVal);
    expect(entity.agentEmail).toBe(agentEmailVal);
  });

  it("entity_model/listingDb/Listing/field_update", () => {
    const entity = new Listing();
    const titleVal = 'test_string';
    const neighbourhoodNameVal = 'hello';
    const kindVal = PropertyKind.Apartment;
    const priceVal = '9.99';
    const bedroomsVal = 100;
    const bathroomsVal = 100;
    const areaSqmVal = 256;
    const statusVal = ListingStatus.Active;
    const agentNameVal = 'hello';
    const publishedAtVal = new Date('2024-06-20T08:30:00Z');
    const summaryVal = 'Description text used for validation';
    const cityVal = 'test_string';
    const latitudeVal = 0.5;
    const longitudeVal = 99.9;
    const agentEmailVal = 'user@example.com';
    entity.title = titleVal;
    entity.neighbourhoodName = neighbourhoodNameVal;
    entity.kind = kindVal;
    entity.price = priceVal;
    entity.bedrooms = bedroomsVal;
    entity.bathrooms = bathroomsVal;
    entity.areaSqm = areaSqmVal;
    entity.status = statusVal;
    entity.agentName = agentNameVal;
    entity.publishedAt = publishedAtVal;
    entity.summary = summaryVal;
    entity.city = cityVal;
    entity.latitude = latitudeVal;
    entity.longitude = longitudeVal;
    entity.agentEmail = agentEmailVal;
    expect(entity.title).toBe(titleVal);
    expect(entity.neighbourhoodName).toBe(neighbourhoodNameVal);
    expect(entity.kind).toBe(kindVal);
    expect(entity.price).toBe(priceVal);
    expect(entity.bedrooms).toBe(bedroomsVal);
    expect(entity.bathrooms).toBe(bathroomsVal);
    expect(entity.areaSqm).toBe(areaSqmVal);
    expect(entity.status).toBe(statusVal);
    expect(entity.agentName).toBe(agentNameVal);
    expect(entity.publishedAt).toEqual(publishedAtVal);
    expect(entity.summary).toBe(summaryVal);
    expect(entity.city).toBe(cityVal);
    expect(entity.latitude).toBe(latitudeVal);
    expect(entity.longitude).toBe(longitudeVal);
    expect(entity.agentEmail).toBe(agentEmailVal);
  });

  it("entity_model/listingDb/Listing/tablename", () => {
    const meta = MetadataStorage.getMetadataFromDecorator(Listing);
    expect(typeof meta.tableName).toBe('string');
    expect(meta.tableName.length).toBeGreaterThan(0);
  });

  it("entity_model/listingDb/Listing/title/max_length", () => {
    expect(propertyMetadata('title').length).toBe(200);
  });

  it("entity_model/listingDb/Listing/neighbourhoodName/max_length", () => {
    expect(propertyMetadata('neighbourhoodName').length).toBe(120);
  });

  it("entity_model/listingDb/Listing/agentName/max_length", () => {
    expect(propertyMetadata('agentName').length).toBe(200);
  });

  it("entity_model/listingDb/Listing/city/max_length", () => {
    expect(propertyMetadata('city').length).toBe(120);
  });

  it("entity_model/listingDb/Listing/status/index", () => {
    const entity = new Listing();
    entity.status = ListingStatus.Draft;
    expect(entity.status).toBeDefined();
  });

  it("entity_model/listingDb/Listing/agentEmail/index", () => {
    const entity = new Listing();
    entity.agentEmail = 'hello@world.com';
    expect(entity.agentEmail).toBeDefined();
  });

  it("entity_model/listingDb/Listing/kind/enum_round_trip", () => {
    const entity = new Listing();
    entity.kind = PropertyKind.House;
    expect(entity.kind).toBe(PropertyKind.House);
    entity.kind = PropertyKind.Apartment;
    expect(entity.kind).toBe(PropertyKind.Apartment);
    entity.kind = PropertyKind.Townhouse;
    expect(entity.kind).toBe(PropertyKind.Townhouse);
    entity.kind = PropertyKind.Cottage;
    expect(entity.kind).toBe(PropertyKind.Cottage);
    entity.kind = PropertyKind.Land;
    expect(entity.kind).toBe(PropertyKind.Land);
  });

  it("entity_model/listingDb/Listing/status/enum_round_trip", () => {
    const entity = new Listing();
    entity.status = ListingStatus.Draft;
    expect(entity.status).toBe(ListingStatus.Draft);
    entity.status = ListingStatus.Active;
    expect(entity.status).toBe(ListingStatus.Active);
    entity.status = ListingStatus.UnderOffer;
    expect(entity.status).toBe(ListingStatus.UnderOffer);
    entity.status = ListingStatus.Sold;
    expect(entity.status).toBe(ListingStatus.Sold);
    entity.status = ListingStatus.Withdrawn;
    expect(entity.status).toBe(ListingStatus.Withdrawn);
  });

  it("entity_model/listingDb/Listing/server_managed_fields", () => {
    const entity = new Listing();
    expect(entity.createdAt).toBeUndefined();
    expect(entity.updatedAt).toBeUndefined();
    expect(entity.id).toBeUndefined();
  });
});
