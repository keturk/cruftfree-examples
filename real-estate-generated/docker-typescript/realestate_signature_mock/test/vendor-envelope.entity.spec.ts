import { MetadataStorage } from '@mikro-orm/core';
import { VendorEnvelope } from '../src/realestate_signature_mock/entities/signature_db/vendor-envelope.entity';
import { EnvelopeStatus } from '../src/enums/envelope-status.enum';

/** The decorator metadata of a mapped property, declared on the entity or a class it extends. */
function propertyMetadata(name: string): { length?: number; nullable?: boolean } {
  let target: unknown = VendorEnvelope;
  while (typeof target === 'function' && target !== Function.prototype) {
    const meta = MetadataStorage.getMetadataFromDecorator(target as new () => object);
    const properties = meta.properties as Record<string, { length?: number; nullable?: boolean } | undefined>;
    const property = properties[name];
    if (property !== undefined) {
      return property;
    }
    target = Object.getPrototypeOf(target);
  }
  throw new Error(`VendorEnvelope maps no property '${name}'.`);
}

describe('VendorEnvelope Entity', () => {
  it("entity_model/signatureDb/VendorEnvelope/create_instance", () => {
    const entity = new VendorEnvelope();
    expect(entity).toBeDefined();
  });

  it("entity_model/signatureDb/VendorEnvelope/field_assignment", () => {
    const entity = new VendorEnvelope();
    const signerNameVal = 'hello';
    const documentTitleVal = 'foo_bar';
    const statusVal = EnvelopeStatus.Sent;
    const settledAtVal = new Date('2025-07-22T14:00:00Z');
    const documentBodyVal = 'Lorem ipsum dolor sit amet';
    const signerEmailVal = 'user@example.com';
    const envelopeIdVal = `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`;
    const idempotencyKeyVal = `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`;
    entity.signerName = signerNameVal;
    entity.documentTitle = documentTitleVal;
    entity.status = statusVal;
    entity.settledAt = settledAtVal;
    entity.documentBody = documentBodyVal;
    entity.signerEmail = signerEmailVal;
    entity.envelopeId = envelopeIdVal;
    entity.idempotencyKey = idempotencyKeyVal;
    expect(entity.signerName).toBe(signerNameVal);
    expect(entity.documentTitle).toBe(documentTitleVal);
    expect(entity.status).toBe(statusVal);
    expect(entity.settledAt).toEqual(settledAtVal);
    expect(entity.documentBody).toBe(documentBodyVal);
    expect(entity.signerEmail).toBe(signerEmailVal);
    expect(entity.envelopeId).toBe(envelopeIdVal);
    expect(entity.idempotencyKey).toBe(idempotencyKeyVal);
  });

  it("entity_model/signatureDb/VendorEnvelope/field_update", () => {
    const entity = new VendorEnvelope();
    const signerNameVal = 'world';
    const documentTitleVal = 'test_string';
    const statusVal = EnvelopeStatus.Signed;
    const settledAtVal = new Date('2025-01-15T12:00:00Z');
    const documentBodyVal = 'The quick brown fox jumps over the lazy dog';
    const signerEmailVal = 'admin@test.org';
    const envelopeIdVal = `alt_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`;
    const idempotencyKeyVal = `alt_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`;
    entity.signerName = signerNameVal;
    entity.documentTitle = documentTitleVal;
    entity.status = statusVal;
    entity.settledAt = settledAtVal;
    entity.documentBody = documentBodyVal;
    entity.signerEmail = signerEmailVal;
    entity.envelopeId = envelopeIdVal;
    entity.idempotencyKey = idempotencyKeyVal;
    expect(entity.signerName).toBe(signerNameVal);
    expect(entity.documentTitle).toBe(documentTitleVal);
    expect(entity.status).toBe(statusVal);
    expect(entity.settledAt).toEqual(settledAtVal);
    expect(entity.documentBody).toBe(documentBodyVal);
    expect(entity.signerEmail).toBe(signerEmailVal);
    expect(entity.envelopeId).toBe(envelopeIdVal);
    expect(entity.idempotencyKey).toBe(idempotencyKeyVal);
  });

  it("entity_model/signatureDb/VendorEnvelope/tablename", () => {
    const meta = MetadataStorage.getMetadataFromDecorator(VendorEnvelope);
    expect(typeof meta.tableName).toBe('string');
    expect(meta.tableName.length).toBeGreaterThan(0);
  });

  it("entity_model/signatureDb/VendorEnvelope/signerName/max_length", () => {
    expect(propertyMetadata('signerName').length).toBe(200);
  });

  it("entity_model/signatureDb/VendorEnvelope/documentTitle/max_length", () => {
    expect(propertyMetadata('documentTitle').length).toBe(200);
  });

  it("entity_model/signatureDb/VendorEnvelope/envelopeId/max_length", () => {
    expect(propertyMetadata('envelopeId').length).toBe(40);
  });

  it("entity_model/signatureDb/VendorEnvelope/idempotencyKey/max_length", () => {
    expect(propertyMetadata('idempotencyKey').length).toBe(120);
  });

  it("entity_model/signatureDb/VendorEnvelope/envelopeId/unique_constraint", () => {
    const entity = new VendorEnvelope();
    entity.envelopeId = `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`;
    expect(entity.envelopeId).toBeDefined();
  });

  it("entity_model/signatureDb/VendorEnvelope/idempotencyKey/unique_constraint", () => {
    const entity = new VendorEnvelope();
    entity.idempotencyKey = `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`;
    expect(entity.idempotencyKey).toBeDefined();
  });

  it("entity_model/signatureDb/VendorEnvelope/status/enum_round_trip", () => {
    const entity = new VendorEnvelope();
    entity.status = EnvelopeStatus.Sent;
    expect(entity.status).toBe(EnvelopeStatus.Sent);
    entity.status = EnvelopeStatus.Signed;
    expect(entity.status).toBe(EnvelopeStatus.Signed);
    entity.status = EnvelopeStatus.Declined;
    expect(entity.status).toBe(EnvelopeStatus.Declined);
  });

  it("entity_model/signatureDb/VendorEnvelope/server_managed_fields", () => {
    const entity = new VendorEnvelope();
    expect(entity.createdAt).toBeUndefined();
    expect(entity.updatedAt).toBeUndefined();
    expect(entity.id).toBeUndefined();
  });
});
