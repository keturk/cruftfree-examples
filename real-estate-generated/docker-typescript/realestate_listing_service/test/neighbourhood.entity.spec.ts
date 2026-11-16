import { MetadataStorage } from '@mikro-orm/core';
import { Neighbourhood } from '../src/realestate_listing_service/entities/listing_db/neighbourhood.entity';

/** The decorator metadata of a mapped property, declared on the entity or a class it extends. */
function propertyMetadata(name: string): { length?: number; nullable?: boolean } {
  let target: unknown = Neighbourhood;
  while (typeof target === 'function' && target !== Function.prototype) {
    const meta = MetadataStorage.getMetadataFromDecorator(target as new () => object);
    const properties = meta.properties as Record<string, { length?: number; nullable?: boolean } | undefined>;
    const property = properties[name];
    if (property !== undefined) {
      return property;
    }
    target = Object.getPrototypeOf(target);
  }
  throw new Error(`Neighbourhood maps no property '${name}'.`);
}

describe('Neighbourhood Entity', () => {
  it("entity_model/listingDb/Neighbourhood/create_instance", () => {
    const entity = new Neighbourhood();
    expect(entity).toBeDefined();
  });

  it("entity_model/listingDb/Neighbourhood/field_assignment", () => {
    const entity = new Neighbourhood();
    const nameVal = `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`;
    const cityVal = 'world';
    const latitudeVal = 3.14;
    const longitudeVal = 1.0;
    entity.name = nameVal;
    entity.city = cityVal;
    entity.latitude = latitudeVal;
    entity.longitude = longitudeVal;
    expect(entity.name).toBe(nameVal);
    expect(entity.city).toBe(cityVal);
    expect(entity.latitude).toBe(latitudeVal);
    expect(entity.longitude).toBe(longitudeVal);
  });

  it("entity_model/listingDb/Neighbourhood/field_update", () => {
    const entity = new Neighbourhood();
    const nameVal = `alt_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`;
    const cityVal = 'foo_bar';
    const latitudeVal = 2.718;
    const longitudeVal = 3.14;
    entity.name = nameVal;
    entity.city = cityVal;
    entity.latitude = latitudeVal;
    entity.longitude = longitudeVal;
    expect(entity.name).toBe(nameVal);
    expect(entity.city).toBe(cityVal);
    expect(entity.latitude).toBe(latitudeVal);
    expect(entity.longitude).toBe(longitudeVal);
  });

  it("entity_model/listingDb/Neighbourhood/tablename", () => {
    const meta = MetadataStorage.getMetadataFromDecorator(Neighbourhood);
    expect(typeof meta.tableName).toBe('string');
    expect(meta.tableName.length).toBeGreaterThan(0);
  });

  it("entity_model/listingDb/Neighbourhood/name/max_length", () => {
    expect(propertyMetadata('name').length).toBe(120);
  });

  it("entity_model/listingDb/Neighbourhood/city/max_length", () => {
    expect(propertyMetadata('city').length).toBe(120);
  });

  it("entity_model/listingDb/Neighbourhood/name/unique_constraint", () => {
    const entity = new Neighbourhood();
    entity.name = `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`;
    expect(entity.name).toBeDefined();
  });

  it("entity_model/listingDb/Neighbourhood/server_managed_fields", () => {
    const entity = new Neighbourhood();
    expect(entity.createdAt).toBeUndefined();
    expect(entity.updatedAt).toBeUndefined();
    expect(entity.id).toBeUndefined();
  });
});
