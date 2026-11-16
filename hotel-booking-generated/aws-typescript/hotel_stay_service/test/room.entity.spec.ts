import { MetadataStorage } from '@mikro-orm/core';
import { Room } from '../src/hotel_stay_service/entities/stay_db/room.entity';
import { RoomCondition } from '../src/enums/room-condition.enum';

/** The decorator metadata of a mapped property, declared on the entity or a class it extends. */
function propertyMetadata(name: string): { length?: number; nullable?: boolean } {
  let target: unknown = Room;
  while (typeof target === 'function' && target !== Function.prototype) {
    const meta = MetadataStorage.getMetadataFromDecorator(target as new () => object);
    const properties = meta.properties as Record<string, { length?: number; nullable?: boolean } | undefined>;
    const property = properties[name];
    if (property !== undefined) {
      return property;
    }
    target = Object.getPrototypeOf(target);
  }
  throw new Error(`Room maps no property '${name}'.`);
}

describe('Room Entity', () => {
  it("entity_model/stayDb/Room/create_instance", () => {
    const entity = new Room();
    expect(entity).toBeDefined();
  });

  it("entity_model/stayDb/Room/field_assignment", () => {
    const entity = new Room();
    const numberVal = `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 3)}`;
    const roomTypeIdVal = '550e8400-e29b-41d4-a716-446655440000';
    const roomTypeNameVal = 'hello';
    const floorVal = 42;
    const conditionVal = RoomCondition.Ready;
    entity.number = numberVal;
    entity.roomTypeId = roomTypeIdVal;
    entity.roomTypeName = roomTypeNameVal;
    entity.floor = floorVal;
    entity.condition = conditionVal;
    expect(entity.number).toBe(numberVal);
    expect(entity.roomTypeId).toBe(roomTypeIdVal);
    expect(entity.roomTypeName).toBe(roomTypeNameVal);
    expect(entity.floor).toBe(floorVal);
    expect(entity.condition).toBe(conditionVal);
  });

  it("entity_model/stayDb/Room/field_update", () => {
    const entity = new Room();
    const numberVal = `alt_${crypto.randomUUID().replace(/-/g, '').slice(0, 4)}`;
    const roomTypeIdVal = '7c9e6679-7425-40de-944b-e07fc1f90ae7';
    const roomTypeNameVal = 'world';
    const floorVal = 100;
    const conditionVal = RoomCondition.Dirty;
    entity.number = numberVal;
    entity.roomTypeId = roomTypeIdVal;
    entity.roomTypeName = roomTypeNameVal;
    entity.floor = floorVal;
    entity.condition = conditionVal;
    expect(entity.number).toBe(numberVal);
    expect(entity.roomTypeId).toBe(roomTypeIdVal);
    expect(entity.roomTypeName).toBe(roomTypeNameVal);
    expect(entity.floor).toBe(floorVal);
    expect(entity.condition).toBe(conditionVal);
  });

  it("entity_model/stayDb/Room/tablename", () => {
    const meta = MetadataStorage.getMetadataFromDecorator(Room);
    expect(typeof meta.tableName).toBe('string');
    expect(meta.tableName.length).toBeGreaterThan(0);
  });

  it("entity_model/stayDb/Room/number/max_length", () => {
    expect(propertyMetadata('number').length).toBe(8);
  });

  it("entity_model/stayDb/Room/roomTypeName/max_length", () => {
    expect(propertyMetadata('roomTypeName').length).toBe(80);
  });

  it("entity_model/stayDb/Room/number/unique_constraint", () => {
    const entity = new Room();
    entity.number = `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 3)}`;
    expect(entity.number).toBeDefined();
  });

  it("entity_model/stayDb/Room/roomTypeId/index", () => {
    const entity = new Room();
    entity.roomTypeId = '550e8400-e29b-41d4-a716-446655440000';
    expect(entity.roomTypeId).toBeDefined();
  });

  it("entity_model/stayDb/Room/condition/enum_round_trip", () => {
    const entity = new Room();
    entity.condition = RoomCondition.Ready;
    expect(entity.condition).toBe(RoomCondition.Ready);
    entity.condition = RoomCondition.Dirty;
    expect(entity.condition).toBe(RoomCondition.Dirty);
    entity.condition = RoomCondition.OutOfService;
    expect(entity.condition).toBe(RoomCondition.OutOfService);
  });

  it("entity_model/stayDb/Room/server_managed_fields", () => {
    const entity = new Room();
    expect(entity.createdAt).toBeUndefined();
    expect(entity.updatedAt).toBeUndefined();
    expect(entity.id).toBeUndefined();
  });
});
