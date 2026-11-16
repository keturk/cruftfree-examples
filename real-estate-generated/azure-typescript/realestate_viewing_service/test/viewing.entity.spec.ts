import { MetadataStorage } from '@mikro-orm/core';
import { Viewing } from '../src/realestate_viewing_service/entities/viewing_db/viewing.entity';
import { ViewingStatus } from '../src/enums/viewing-status.enum';

/** The decorator metadata of a mapped property, declared on the entity or a class it extends. */
function propertyMetadata(name: string): { length?: number; nullable?: boolean } {
  let target: unknown = Viewing;
  while (typeof target === 'function' && target !== Function.prototype) {
    const meta = MetadataStorage.getMetadataFromDecorator(target as new () => object);
    const properties = meta.properties as Record<string, { length?: number; nullable?: boolean } | undefined>;
    const property = properties[name];
    if (property !== undefined) {
      return property;
    }
    target = Object.getPrototypeOf(target);
  }
  throw new Error(`Viewing maps no property '${name}'.`);
}

describe('Viewing Entity', () => {
  it("entity_model/viewingDb/Viewing/create_instance", () => {
    const entity = new Viewing();
    expect(entity).toBeDefined();
  });

  it("entity_model/viewingDb/Viewing/field_assignment", () => {
    const entity = new Viewing();
    const startsAtVal = new Date('2025-01-15T12:00:00Z');
    const endsAtVal = new Date('2025-03-10T16:45:00Z');
    const listingTitleVal = 'hello';
    const buyerNameVal = 'world';
    const statusVal = ViewingStatus.Requested;
    const agentNameVal = 'world';
    const noteVal = 'test_string';
    const listingIdVal = '550e8400-e29b-41d4-a716-446655440000';
    const buyerEmailVal = 'admin@test.org';
    const agentEmailVal = 'info@sample.net';
    const reminderSentVal = false;
    entity.startsAt = startsAtVal;
    entity.endsAt = endsAtVal;
    entity.listingTitle = listingTitleVal;
    entity.buyerName = buyerNameVal;
    entity.status = statusVal;
    entity.agentName = agentNameVal;
    entity.note = noteVal;
    entity.listingId = listingIdVal;
    entity.buyerEmail = buyerEmailVal;
    entity.agentEmail = agentEmailVal;
    entity.reminderSent = reminderSentVal;
    expect(entity.startsAt).toEqual(startsAtVal);
    expect(entity.endsAt).toEqual(endsAtVal);
    expect(entity.listingTitle).toBe(listingTitleVal);
    expect(entity.buyerName).toBe(buyerNameVal);
    expect(entity.status).toBe(statusVal);
    expect(entity.agentName).toBe(agentNameVal);
    expect(entity.note).toBe(noteVal);
    expect(entity.listingId).toBe(listingIdVal);
    expect(entity.buyerEmail).toBe(buyerEmailVal);
    expect(entity.agentEmail).toBe(agentEmailVal);
    expect(entity.reminderSent).toBe(reminderSentVal);
  });

  it("entity_model/viewingDb/Viewing/field_update", () => {
    const entity = new Viewing();
    const startsAtVal = new Date('2024-06-20T08:30:00Z');
    const endsAtVal = new Date('2024-11-05T09:15:00Z');
    const listingTitleVal = 'world';
    const buyerNameVal = 'foo_bar';
    const statusVal = ViewingStatus.Confirmed;
    const agentNameVal = 'foo_bar';
    const noteVal = 'sample_text';
    const listingIdVal = '6ba7b810-9dad-11d1-80b4-00c04fd430c8';
    const buyerEmailVal = 'info@sample.net';
    const agentEmailVal = 'test@demo.io';
    const reminderSentVal = true;
    entity.startsAt = startsAtVal;
    entity.endsAt = endsAtVal;
    entity.listingTitle = listingTitleVal;
    entity.buyerName = buyerNameVal;
    entity.status = statusVal;
    entity.agentName = agentNameVal;
    entity.note = noteVal;
    entity.listingId = listingIdVal;
    entity.buyerEmail = buyerEmailVal;
    entity.agentEmail = agentEmailVal;
    entity.reminderSent = reminderSentVal;
    expect(entity.startsAt).toEqual(startsAtVal);
    expect(entity.endsAt).toEqual(endsAtVal);
    expect(entity.listingTitle).toBe(listingTitleVal);
    expect(entity.buyerName).toBe(buyerNameVal);
    expect(entity.status).toBe(statusVal);
    expect(entity.agentName).toBe(agentNameVal);
    expect(entity.note).toBe(noteVal);
    expect(entity.listingId).toBe(listingIdVal);
    expect(entity.buyerEmail).toBe(buyerEmailVal);
    expect(entity.agentEmail).toBe(agentEmailVal);
    expect(entity.reminderSent).toBe(reminderSentVal);
  });

  it("entity_model/viewingDb/Viewing/tablename", () => {
    const meta = MetadataStorage.getMetadataFromDecorator(Viewing);
    expect(typeof meta.tableName).toBe('string');
    expect(meta.tableName.length).toBeGreaterThan(0);
  });

  it("entity_model/viewingDb/Viewing/listingTitle/max_length", () => {
    expect(propertyMetadata('listingTitle').length).toBe(200);
  });

  it("entity_model/viewingDb/Viewing/buyerName/max_length", () => {
    expect(propertyMetadata('buyerName').length).toBe(200);
  });

  it("entity_model/viewingDb/Viewing/agentName/max_length", () => {
    expect(propertyMetadata('agentName').length).toBe(200);
  });

  it("entity_model/viewingDb/Viewing/note/max_length", () => {
    expect(propertyMetadata('note').length).toBe(500);
  });

  it("entity_model/viewingDb/Viewing/listingId/index", () => {
    const entity = new Viewing();
    entity.listingId = '550e8400-e29b-41d4-a716-446655440000';
    expect(entity.listingId).toBeDefined();
  });

  it("entity_model/viewingDb/Viewing/buyerEmail/index", () => {
    const entity = new Viewing();
    entity.buyerEmail = 'admin@test.org';
    expect(entity.buyerEmail).toBeDefined();
  });

  it("entity_model/viewingDb/Viewing/agentEmail/index", () => {
    const entity = new Viewing();
    entity.agentEmail = 'info@sample.net';
    expect(entity.agentEmail).toBeDefined();
  });

  it("entity_model/viewingDb/Viewing/status/enum_round_trip", () => {
    const entity = new Viewing();
    entity.status = ViewingStatus.Requested;
    expect(entity.status).toBe(ViewingStatus.Requested);
    entity.status = ViewingStatus.Confirmed;
    expect(entity.status).toBe(ViewingStatus.Confirmed);
    entity.status = ViewingStatus.Completed;
    expect(entity.status).toBe(ViewingStatus.Completed);
    entity.status = ViewingStatus.Cancelled;
    expect(entity.status).toBe(ViewingStatus.Cancelled);
    entity.status = ViewingStatus.NoShow;
    expect(entity.status).toBe(ViewingStatus.NoShow);
  });

  it("entity_model/viewingDb/Viewing/server_managed_fields", () => {
    const entity = new Viewing();
    expect(entity.createdAt).toBeUndefined();
    expect(entity.updatedAt).toBeUndefined();
    expect(entity.id).toBeUndefined();
  });
});
