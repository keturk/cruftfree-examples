import { MetadataStorage } from '@mikro-orm/core';
import { PublishedNight } from '../src/hotel_channel_mock/entities/channel_db/published-night.entity';

/** The decorator metadata of a mapped property, declared on the entity or a class it extends. */
function propertyMetadata(name: string): { length?: number; nullable?: boolean } {
  let target: unknown = PublishedNight;
  while (typeof target === 'function' && target !== Function.prototype) {
    const meta = MetadataStorage.getMetadataFromDecorator(target as new () => object);
    const properties = meta.properties as Record<string, { length?: number; nullable?: boolean } | undefined>;
    const property = properties[name];
    if (property !== undefined) {
      return property;
    }
    target = Object.getPrototypeOf(target);
  }
  throw new Error(`PublishedNight maps no property '${name}'.`);
}

describe('PublishedNight Entity', () => {
  it("entity_model/channelDb/PublishedNight/create_instance", () => {
    const entity = new PublishedNight();
    expect(entity).toBeDefined();
  });

  it("entity_model/channelDb/PublishedNight/field_assignment", () => {
    const entity = new PublishedNight();
    const roomTypeVal = 'test_string';
    const nightVal = '2024-06-20';
    const leftVal = 256;
    const nightlyRateVal = '149.00';
    const receivedAtVal = new Date('2025-07-22T14:00:00Z');
    entity.roomType = roomTypeVal;
    entity.night = nightVal;
    entity.left = leftVal;
    entity.nightlyRate = nightlyRateVal;
    entity.receivedAt = receivedAtVal;
    expect(entity.roomType).toBe(roomTypeVal);
    expect(entity.night).toEqual(nightVal);
    expect(entity.left).toBe(leftVal);
    expect(entity.nightlyRate).toBe(nightlyRateVal);
    expect(entity.receivedAt).toEqual(receivedAtVal);
  });

  it("entity_model/channelDb/PublishedNight/field_update", () => {
    const entity = new PublishedNight();
    const roomTypeVal = 'sample_text';
    const nightVal = '2025-03-10';
    const leftVal = 1;
    const nightlyRateVal = '4.50';
    const receivedAtVal = new Date('2025-01-15T12:00:00Z');
    entity.roomType = roomTypeVal;
    entity.night = nightVal;
    entity.left = leftVal;
    entity.nightlyRate = nightlyRateVal;
    entity.receivedAt = receivedAtVal;
    expect(entity.roomType).toBe(roomTypeVal);
    expect(entity.night).toEqual(nightVal);
    expect(entity.left).toBe(leftVal);
    expect(entity.nightlyRate).toBe(nightlyRateVal);
    expect(entity.receivedAt).toEqual(receivedAtVal);
  });

  it("entity_model/channelDb/PublishedNight/tablename", () => {
    const meta = MetadataStorage.getMetadataFromDecorator(PublishedNight);
    expect(typeof meta.tableName).toBe('string');
    expect(meta.tableName.length).toBeGreaterThan(0);
  });

  it("entity_model/channelDb/PublishedNight/roomType/max_length", () => {
    expect(propertyMetadata('roomType').length).toBe(80);
  });

  it("entity_model/channelDb/PublishedNight/server_managed_fields", () => {
    const entity = new PublishedNight();
    expect(entity.createdAt).toBeUndefined();
    expect(entity.updatedAt).toBeUndefined();
    expect(entity.id).toBeUndefined();
  });
});
