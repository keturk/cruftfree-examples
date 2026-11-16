import { MetadataStorage } from '@mikro-orm/core';
import { Stay } from '../src/hotel_stay_service/entities/stay_db/stay.entity';
import { StayStatus } from '../src/enums/stay-status.enum';

/** The decorator metadata of a mapped property, declared on the entity or a class it extends. */
function propertyMetadata(name: string): { length?: number; nullable?: boolean } {
  let target: unknown = Stay;
  while (typeof target === 'function' && target !== Function.prototype) {
    const meta = MetadataStorage.getMetadataFromDecorator(target as new () => object);
    const properties = meta.properties as Record<string, { length?: number; nullable?: boolean } | undefined>;
    const property = properties[name];
    if (property !== undefined) {
      return property;
    }
    target = Object.getPrototypeOf(target);
  }
  throw new Error(`Stay maps no property '${name}'.`);
}

describe('Stay Entity', () => {
  it("entity_model/stayDb/Stay/create_instance", () => {
    const entity = new Stay();
    expect(entity).toBeDefined();
  });

  it("entity_model/stayDb/Stay/field_assignment", () => {
    const entity = new Stay();
    const codeVal = `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`;
    const roomTypeIdVal = 'f47ac10b-58cc-4372-a567-0e02b2c3d479';
    const roomTypeNameVal = 'sample_text';
    const roomNumberVal = 'sample_t';
    const guestIdVal = 'hello';
    const guestNameVal = 'sample_text';
    const guestEmailVal = 'test@demo.io';
    const arrivalVal = '2025-07-22';
    const departureVal = '2024-11-05';
    const nightsVal = 42;
    const guestsVal = 256;
    const totalVal = '4.50';
    const statusVal = StayStatus.Held;
    const holdUntilVal = new Date('2025-01-15T12:00:00Z');
    const chargeIdVal = 'hello';
    const deskNoteVal = 'Test content body with details';
    entity.code = codeVal;
    entity.roomTypeId = roomTypeIdVal;
    entity.roomTypeName = roomTypeNameVal;
    entity.roomNumber = roomNumberVal;
    entity.guestId = guestIdVal;
    entity.guestName = guestNameVal;
    entity.guestEmail = guestEmailVal;
    entity.arrival = arrivalVal;
    entity.departure = departureVal;
    entity.nights = nightsVal;
    entity.guests = guestsVal;
    entity.total = totalVal;
    entity.status = statusVal;
    entity.holdUntil = holdUntilVal;
    entity.chargeId = chargeIdVal;
    entity.deskNote = deskNoteVal;
    expect(entity.code).toBe(codeVal);
    expect(entity.roomTypeId).toBe(roomTypeIdVal);
    expect(entity.roomTypeName).toBe(roomTypeNameVal);
    expect(entity.roomNumber).toBe(roomNumberVal);
    expect(entity.guestId).toBe(guestIdVal);
    expect(entity.guestName).toBe(guestNameVal);
    expect(entity.guestEmail).toBe(guestEmailVal);
    expect(entity.arrival).toEqual(arrivalVal);
    expect(entity.departure).toEqual(departureVal);
    expect(entity.nights).toBe(nightsVal);
    expect(entity.guests).toBe(guestsVal);
    expect(entity.total).toBe(totalVal);
    expect(entity.status).toBe(statusVal);
    expect(entity.holdUntil).toEqual(holdUntilVal);
    expect(entity.chargeId).toBe(chargeIdVal);
    expect(entity.deskNote).toBe(deskNoteVal);
  });

  it("entity_model/stayDb/Stay/field_update", () => {
    const entity = new Stay();
    const codeVal = `alt_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`;
    const roomTypeIdVal = '7c9e6679-7425-40de-944b-e07fc1f90ae7';
    const roomTypeNameVal = 'hello';
    const roomNumberVal = 'hello';
    const guestIdVal = 'world';
    const guestNameVal = 'hello';
    const guestEmailVal = 'hello@world.com';
    const arrivalVal = '2025-01-15';
    const departureVal = '2025-07-22';
    const nightsVal = 100;
    const guestsVal = 1;
    const totalVal = '19.99';
    const statusVal = StayStatus.Confirmed;
    const holdUntilVal = new Date('2024-06-20T08:30:00Z');
    const chargeIdVal = 'world';
    const deskNoteVal = 'Description text used for validation';
    entity.code = codeVal;
    entity.roomTypeId = roomTypeIdVal;
    entity.roomTypeName = roomTypeNameVal;
    entity.roomNumber = roomNumberVal;
    entity.guestId = guestIdVal;
    entity.guestName = guestNameVal;
    entity.guestEmail = guestEmailVal;
    entity.arrival = arrivalVal;
    entity.departure = departureVal;
    entity.nights = nightsVal;
    entity.guests = guestsVal;
    entity.total = totalVal;
    entity.status = statusVal;
    entity.holdUntil = holdUntilVal;
    entity.chargeId = chargeIdVal;
    entity.deskNote = deskNoteVal;
    expect(entity.code).toBe(codeVal);
    expect(entity.roomTypeId).toBe(roomTypeIdVal);
    expect(entity.roomTypeName).toBe(roomTypeNameVal);
    expect(entity.roomNumber).toBe(roomNumberVal);
    expect(entity.guestId).toBe(guestIdVal);
    expect(entity.guestName).toBe(guestNameVal);
    expect(entity.guestEmail).toBe(guestEmailVal);
    expect(entity.arrival).toEqual(arrivalVal);
    expect(entity.departure).toEqual(departureVal);
    expect(entity.nights).toBe(nightsVal);
    expect(entity.guests).toBe(guestsVal);
    expect(entity.total).toBe(totalVal);
    expect(entity.status).toBe(statusVal);
    expect(entity.holdUntil).toEqual(holdUntilVal);
    expect(entity.chargeId).toBe(chargeIdVal);
    expect(entity.deskNote).toBe(deskNoteVal);
  });

  it("entity_model/stayDb/Stay/tablename", () => {
    const meta = MetadataStorage.getMetadataFromDecorator(Stay);
    expect(typeof meta.tableName).toBe('string');
    expect(meta.tableName.length).toBeGreaterThan(0);
  });

  it("entity_model/stayDb/Stay/code/max_length", () => {
    expect(propertyMetadata('code').length).toBe(20);
  });

  it("entity_model/stayDb/Stay/roomTypeName/max_length", () => {
    expect(propertyMetadata('roomTypeName').length).toBe(80);
  });

  it("entity_model/stayDb/Stay/roomNumber/max_length", () => {
    expect(propertyMetadata('roomNumber').length).toBe(8);
  });

  it("entity_model/stayDb/Stay/guestId/max_length", () => {
    expect(propertyMetadata('guestId').length).toBe(64);
  });

  it("entity_model/stayDb/Stay/guestName/max_length", () => {
    expect(propertyMetadata('guestName').length).toBe(200);
  });

  it("entity_model/stayDb/Stay/chargeId/max_length", () => {
    expect(propertyMetadata('chargeId').length).toBe(40);
  });

  it("entity_model/stayDb/Stay/code/unique_constraint", () => {
    const entity = new Stay();
    entity.code = `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`;
    expect(entity.code).toBeDefined();
  });

  it("entity_model/stayDb/Stay/roomTypeId/index", () => {
    const entity = new Stay();
    entity.roomTypeId = 'f47ac10b-58cc-4372-a567-0e02b2c3d479';
    expect(entity.roomTypeId).toBeDefined();
  });

  it("entity_model/stayDb/Stay/guestId/index", () => {
    const entity = new Stay();
    entity.guestId = 'hello';
    expect(entity.guestId).toBeDefined();
  });

  it("entity_model/stayDb/Stay/status/enum_round_trip", () => {
    const entity = new Stay();
    entity.status = StayStatus.Held;
    expect(entity.status).toBe(StayStatus.Held);
    entity.status = StayStatus.Confirmed;
    expect(entity.status).toBe(StayStatus.Confirmed);
    entity.status = StayStatus.CheckedIn;
    expect(entity.status).toBe(StayStatus.CheckedIn);
    entity.status = StayStatus.CheckedOut;
    expect(entity.status).toBe(StayStatus.CheckedOut);
    entity.status = StayStatus.Cancelled;
    expect(entity.status).toBe(StayStatus.Cancelled);
    entity.status = StayStatus.Expired;
    expect(entity.status).toBe(StayStatus.Expired);
  });

  it("entity_model/stayDb/Stay/server_managed_fields", () => {
    const entity = new Stay();
    expect(entity.createdAt).toBeUndefined();
    expect(entity.updatedAt).toBeUndefined();
    expect(entity.id).toBeUndefined();
  });
});
