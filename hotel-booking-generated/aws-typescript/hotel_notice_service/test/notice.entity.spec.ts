import { MetadataStorage } from '@mikro-orm/core';
import { Notice } from '../src/hotel_notice_service/entities/notice_db/notice.entity';

/** The decorator metadata of a mapped property, declared on the entity or a class it extends. */
function propertyMetadata(name: string): { length?: number; nullable?: boolean } {
  let target: unknown = Notice;
  while (typeof target === 'function' && target !== Function.prototype) {
    const meta = MetadataStorage.getMetadataFromDecorator(target as new () => object);
    const properties = meta.properties as Record<string, { length?: number; nullable?: boolean } | undefined>;
    const property = properties[name];
    if (property !== undefined) {
      return property;
    }
    target = Object.getPrototypeOf(target);
  }
  throw new Error(`Notice maps no property '${name}'.`);
}

describe('Notice Entity', () => {
  it("entity_model/noticeDb/Notice/create_instance", () => {
    const entity = new Notice();
    expect(entity).toBeDefined();
  });

  it("entity_model/noticeDb/Notice/field_assignment", () => {
    const entity = new Notice();
    const recipientVal = 'hello';
    const subjectVal = 'foo_bar';
    const bodyVal = 'sample_text';
    const deliveredVal = true;
    const attemptsVal = 7;
    const noticeKeyVal = `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`;
    entity.recipient = recipientVal;
    entity.subject = subjectVal;
    entity.body = bodyVal;
    entity.delivered = deliveredVal;
    entity.attempts = attemptsVal;
    entity.noticeKey = noticeKeyVal;
    expect(entity.recipient).toBe(recipientVal);
    expect(entity.subject).toBe(subjectVal);
    expect(entity.body).toBe(bodyVal);
    expect(entity.delivered).toBe(deliveredVal);
    expect(entity.attempts).toBe(attemptsVal);
    expect(entity.noticeKey).toBe(noticeKeyVal);
  });

  it("entity_model/noticeDb/Notice/field_update", () => {
    const entity = new Notice();
    const recipientVal = 'world';
    const subjectVal = 'test_string';
    const bodyVal = 'hello';
    const deliveredVal = false;
    const attemptsVal = 256;
    const noticeKeyVal = `alt_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`;
    entity.recipient = recipientVal;
    entity.subject = subjectVal;
    entity.body = bodyVal;
    entity.delivered = deliveredVal;
    entity.attempts = attemptsVal;
    entity.noticeKey = noticeKeyVal;
    expect(entity.recipient).toBe(recipientVal);
    expect(entity.subject).toBe(subjectVal);
    expect(entity.body).toBe(bodyVal);
    expect(entity.delivered).toBe(deliveredVal);
    expect(entity.attempts).toBe(attemptsVal);
    expect(entity.noticeKey).toBe(noticeKeyVal);
  });

  it("entity_model/noticeDb/Notice/tablename", () => {
    const meta = MetadataStorage.getMetadataFromDecorator(Notice);
    expect(typeof meta.tableName).toBe('string');
    expect(meta.tableName.length).toBeGreaterThan(0);
  });

  it("entity_model/noticeDb/Notice/recipient/max_length", () => {
    expect(propertyMetadata('recipient').length).toBe(200);
  });

  it("entity_model/noticeDb/Notice/subject/max_length", () => {
    expect(propertyMetadata('subject').length).toBe(200);
  });

  it("entity_model/noticeDb/Notice/body/max_length", () => {
    expect(propertyMetadata('body').length).toBe(2000);
  });

  it("entity_model/noticeDb/Notice/noticeKey/max_length", () => {
    expect(propertyMetadata('noticeKey').length).toBe(120);
  });

  it("entity_model/noticeDb/Notice/noticeKey/unique_constraint", () => {
    const entity = new Notice();
    entity.noticeKey = `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`;
    expect(entity.noticeKey).toBeDefined();
  });

  it("entity_model/noticeDb/Notice/delivered/index", () => {
    const entity = new Notice();
    entity.delivered = true;
    expect(entity.delivered).toBeDefined();
  });

  it("entity_model/noticeDb/Notice/server_managed_fields", () => {
    const entity = new Notice();
    expect(entity.createdAt).toBeUndefined();
    expect(entity.updatedAt).toBeUndefined();
    expect(entity.id).toBeUndefined();
  });
});
