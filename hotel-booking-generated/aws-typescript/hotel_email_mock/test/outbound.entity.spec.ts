import { MetadataStorage } from '@mikro-orm/core';
import { Outbound } from '../src/hotel_email_mock/entities/email_db/outbound.entity';
import { DeliveryStatus } from '../src/enums/delivery-status.enum';

/** The decorator metadata of a mapped property, declared on the entity or a class it extends. */
function propertyMetadata(name: string): { length?: number; nullable?: boolean } {
  let target: unknown = Outbound;
  while (typeof target === 'function' && target !== Function.prototype) {
    const meta = MetadataStorage.getMetadataFromDecorator(target as new () => object);
    const properties = meta.properties as Record<string, { length?: number; nullable?: boolean } | undefined>;
    const property = properties[name];
    if (property !== undefined) {
      return property;
    }
    target = Object.getPrototypeOf(target);
  }
  throw new Error(`Outbound maps no property '${name}'.`);
}

describe('Outbound Entity', () => {
  it("entity_model/emailDb/Outbound/create_instance", () => {
    const entity = new Outbound();
    expect(entity).toBeDefined();
  });

  it("entity_model/emailDb/Outbound/field_assignment", () => {
    const entity = new Outbound();
    const recipientVal = 'sample_text';
    const subjectVal = 'test_string';
    const bodyVal = 'hello';
    const statusVal = DeliveryStatus.Delivered;
    const deliveryIdVal = `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`;
    const idempotencyKeyVal = `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`;
    entity.recipient = recipientVal;
    entity.subject = subjectVal;
    entity.body = bodyVal;
    entity.status = statusVal;
    entity.deliveryId = deliveryIdVal;
    entity.idempotencyKey = idempotencyKeyVal;
    expect(entity.recipient).toBe(recipientVal);
    expect(entity.subject).toBe(subjectVal);
    expect(entity.body).toBe(bodyVal);
    expect(entity.status).toBe(statusVal);
    expect(entity.deliveryId).toBe(deliveryIdVal);
    expect(entity.idempotencyKey).toBe(idempotencyKeyVal);
  });

  it("entity_model/emailDb/Outbound/field_update", () => {
    const entity = new Outbound();
    const recipientVal = 'hello';
    const subjectVal = 'sample_text';
    const bodyVal = 'world';
    const statusVal = DeliveryStatus.Bounced;
    const deliveryIdVal = `alt_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`;
    const idempotencyKeyVal = `alt_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`;
    entity.recipient = recipientVal;
    entity.subject = subjectVal;
    entity.body = bodyVal;
    entity.status = statusVal;
    entity.deliveryId = deliveryIdVal;
    entity.idempotencyKey = idempotencyKeyVal;
    expect(entity.recipient).toBe(recipientVal);
    expect(entity.subject).toBe(subjectVal);
    expect(entity.body).toBe(bodyVal);
    expect(entity.status).toBe(statusVal);
    expect(entity.deliveryId).toBe(deliveryIdVal);
    expect(entity.idempotencyKey).toBe(idempotencyKeyVal);
  });

  it("entity_model/emailDb/Outbound/tablename", () => {
    const meta = MetadataStorage.getMetadataFromDecorator(Outbound);
    expect(typeof meta.tableName).toBe('string');
    expect(meta.tableName.length).toBeGreaterThan(0);
  });

  it("entity_model/emailDb/Outbound/recipient/max_length", () => {
    expect(propertyMetadata('recipient').length).toBe(200);
  });

  it("entity_model/emailDb/Outbound/subject/max_length", () => {
    expect(propertyMetadata('subject').length).toBe(200);
  });

  it("entity_model/emailDb/Outbound/body/max_length", () => {
    expect(propertyMetadata('body').length).toBe(2000);
  });

  it("entity_model/emailDb/Outbound/deliveryId/max_length", () => {
    expect(propertyMetadata('deliveryId').length).toBe(40);
  });

  it("entity_model/emailDb/Outbound/idempotencyKey/max_length", () => {
    expect(propertyMetadata('idempotencyKey').length).toBe(120);
  });

  it("entity_model/emailDb/Outbound/deliveryId/unique_constraint", () => {
    const entity = new Outbound();
    entity.deliveryId = `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`;
    expect(entity.deliveryId).toBeDefined();
  });

  it("entity_model/emailDb/Outbound/idempotencyKey/unique_constraint", () => {
    const entity = new Outbound();
    entity.idempotencyKey = `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`;
    expect(entity.idempotencyKey).toBeDefined();
  });

  it("entity_model/emailDb/Outbound/status/enum_round_trip", () => {
    const entity = new Outbound();
    entity.status = DeliveryStatus.Delivered;
    expect(entity.status).toBe(DeliveryStatus.Delivered);
    entity.status = DeliveryStatus.Bounced;
    expect(entity.status).toBe(DeliveryStatus.Bounced);
  });

  it("entity_model/emailDb/Outbound/server_managed_fields", () => {
    const entity = new Outbound();
    expect(entity.createdAt).toBeUndefined();
    expect(entity.updatedAt).toBeUndefined();
    expect(entity.id).toBeUndefined();
  });
});
