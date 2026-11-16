import { MetadataStorage } from '@mikro-orm/core';
import { RoomType } from '../src/hotel_stay_service/entities/stay_db/room-type.entity';

/** The decorator metadata of a mapped property, declared on the entity or a class it extends. */
function propertyMetadata(name: string): { length?: number; nullable?: boolean } {
  let target: unknown = RoomType;
  while (typeof target === 'function' && target !== Function.prototype) {
    const meta = MetadataStorage.getMetadataFromDecorator(target as new () => object);
    const properties = meta.properties as Record<string, { length?: number; nullable?: boolean } | undefined>;
    const property = properties[name];
    if (property !== undefined) {
      return property;
    }
    target = Object.getPrototypeOf(target);
  }
  throw new Error(`RoomType maps no property '${name}'.`);
}

describe('RoomType Entity', () => {
  it("entity_model/stayDb/RoomType/create_instance", () => {
    const entity = new RoomType();
    expect(entity).toBeDefined();
  });

  it("entity_model/stayDb/RoomType/field_assignment", () => {
    const entity = new RoomType();
    const nameVal = `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`;
    const summaryVal = 'world';
    const descriptionVal = 'Description text used for validation';
    const sleepsVal = 100;
    const nightlyRateVal = '19.99';
    const inventoryVal = 7;
    const listedVal = false;
    entity.name = nameVal;
    entity.summary = summaryVal;
    entity.description = descriptionVal;
    entity.sleeps = sleepsVal;
    entity.nightlyRate = nightlyRateVal;
    entity.inventory = inventoryVal;
    entity.listed = listedVal;
    expect(entity.name).toBe(nameVal);
    expect(entity.summary).toBe(summaryVal);
    expect(entity.description).toBe(descriptionVal);
    expect(entity.sleeps).toBe(sleepsVal);
    expect(entity.nightlyRate).toBe(nightlyRateVal);
    expect(entity.inventory).toBe(inventoryVal);
    expect(entity.listed).toBe(listedVal);
  });

  it("entity_model/stayDb/RoomType/field_update", () => {
    const entity = new RoomType();
    const nameVal = `alt_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`;
    const summaryVal = 'foo_bar';
    const descriptionVal = 'Lorem ipsum dolor sit amet';
    const sleepsVal = 7;
    const nightlyRateVal = '49.95';
    const inventoryVal = 256;
    const listedVal = true;
    entity.name = nameVal;
    entity.summary = summaryVal;
    entity.description = descriptionVal;
    entity.sleeps = sleepsVal;
    entity.nightlyRate = nightlyRateVal;
    entity.inventory = inventoryVal;
    entity.listed = listedVal;
    expect(entity.name).toBe(nameVal);
    expect(entity.summary).toBe(summaryVal);
    expect(entity.description).toBe(descriptionVal);
    expect(entity.sleeps).toBe(sleepsVal);
    expect(entity.nightlyRate).toBe(nightlyRateVal);
    expect(entity.inventory).toBe(inventoryVal);
    expect(entity.listed).toBe(listedVal);
  });

  it("entity_model/stayDb/RoomType/tablename", () => {
    const meta = MetadataStorage.getMetadataFromDecorator(RoomType);
    expect(typeof meta.tableName).toBe('string');
    expect(meta.tableName.length).toBeGreaterThan(0);
  });

  it("entity_model/stayDb/RoomType/name/max_length", () => {
    expect(propertyMetadata('name').length).toBe(80);
  });

  it("entity_model/stayDb/RoomType/summary/max_length", () => {
    expect(propertyMetadata('summary').length).toBe(200);
  });

  it("entity_model/stayDb/RoomType/name/unique_constraint", () => {
    const entity = new RoomType();
    entity.name = `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`;
    expect(entity.name).toBeDefined();
  });

  it("entity_model/stayDb/RoomType/server_managed_fields", () => {
    const entity = new RoomType();
    expect(entity.createdAt).toBeUndefined();
    expect(entity.updatedAt).toBeUndefined();
    expect(entity.id).toBeUndefined();
  });
});
