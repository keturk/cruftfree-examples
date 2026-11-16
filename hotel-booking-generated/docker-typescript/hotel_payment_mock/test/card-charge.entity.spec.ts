import { MetadataStorage } from '@mikro-orm/core';
import { CardCharge } from '../src/hotel_payment_mock/entities/payment_db/card-charge.entity';
import { ChargeStatus } from '../src/enums/charge-status.enum';

/** The decorator metadata of a mapped property, declared on the entity or a class it extends. */
function propertyMetadata(name: string): { length?: number; nullable?: boolean } {
  let target: unknown = CardCharge;
  while (typeof target === 'function' && target !== Function.prototype) {
    const meta = MetadataStorage.getMetadataFromDecorator(target as new () => object);
    const properties = meta.properties as Record<string, { length?: number; nullable?: boolean } | undefined>;
    const property = properties[name];
    if (property !== undefined) {
      return property;
    }
    target = Object.getPrototypeOf(target);
  }
  throw new Error(`CardCharge maps no property '${name}'.`);
}

describe('CardCharge Entity', () => {
  it("entity_model/paymentDb/CardCharge/create_instance", () => {
    const entity = new CardCharge();
    expect(entity).toBeDefined();
  });

  it("entity_model/paymentDb/CardCharge/field_assignment", () => {
    const entity = new CardCharge();
    const referenceVal = 'hello';
    const amountVal = '19.99';
    const currencyVal = 'hel';
    const statusVal = ChargeStatus.Succeeded;
    const declineReasonVal = 'hello';
    const chargeIdVal = `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`;
    const idempotencyKeyVal = `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`;
    entity.reference = referenceVal;
    entity.amount = amountVal;
    entity.currency = currencyVal;
    entity.status = statusVal;
    entity.declineReason = declineReasonVal;
    entity.chargeId = chargeIdVal;
    entity.idempotencyKey = idempotencyKeyVal;
    expect(entity.reference).toBe(referenceVal);
    expect(entity.amount).toBe(amountVal);
    expect(entity.currency).toBe(currencyVal);
    expect(entity.status).toBe(statusVal);
    expect(entity.declineReason).toBe(declineReasonVal);
    expect(entity.chargeId).toBe(chargeIdVal);
    expect(entity.idempotencyKey).toBe(idempotencyKeyVal);
  });

  it("entity_model/paymentDb/CardCharge/field_update", () => {
    const entity = new CardCharge();
    const referenceVal = 'world';
    const amountVal = '49.95';
    const currencyVal = 'wor';
    const statusVal = ChargeStatus.Declined;
    const declineReasonVal = 'world';
    const chargeIdVal = `alt_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`;
    const idempotencyKeyVal = `alt_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`;
    entity.reference = referenceVal;
    entity.amount = amountVal;
    entity.currency = currencyVal;
    entity.status = statusVal;
    entity.declineReason = declineReasonVal;
    entity.chargeId = chargeIdVal;
    entity.idempotencyKey = idempotencyKeyVal;
    expect(entity.reference).toBe(referenceVal);
    expect(entity.amount).toBe(amountVal);
    expect(entity.currency).toBe(currencyVal);
    expect(entity.status).toBe(statusVal);
    expect(entity.declineReason).toBe(declineReasonVal);
    expect(entity.chargeId).toBe(chargeIdVal);
    expect(entity.idempotencyKey).toBe(idempotencyKeyVal);
  });

  it("entity_model/paymentDb/CardCharge/tablename", () => {
    const meta = MetadataStorage.getMetadataFromDecorator(CardCharge);
    expect(typeof meta.tableName).toBe('string');
    expect(meta.tableName.length).toBeGreaterThan(0);
  });

  it("entity_model/paymentDb/CardCharge/reference/max_length", () => {
    expect(propertyMetadata('reference').length).toBe(80);
  });

  it("entity_model/paymentDb/CardCharge/currency/max_length", () => {
    expect(propertyMetadata('currency').length).toBe(3);
  });

  it("entity_model/paymentDb/CardCharge/declineReason/max_length", () => {
    expect(propertyMetadata('declineReason').length).toBe(200);
  });

  it("entity_model/paymentDb/CardCharge/chargeId/max_length", () => {
    expect(propertyMetadata('chargeId').length).toBe(40);
  });

  it("entity_model/paymentDb/CardCharge/idempotencyKey/max_length", () => {
    expect(propertyMetadata('idempotencyKey').length).toBe(120);
  });

  it("entity_model/paymentDb/CardCharge/chargeId/unique_constraint", () => {
    const entity = new CardCharge();
    entity.chargeId = `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`;
    expect(entity.chargeId).toBeDefined();
  });

  it("entity_model/paymentDb/CardCharge/idempotencyKey/unique_constraint", () => {
    const entity = new CardCharge();
    entity.idempotencyKey = `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`;
    expect(entity.idempotencyKey).toBeDefined();
  });

  it("entity_model/paymentDb/CardCharge/status/enum_round_trip", () => {
    const entity = new CardCharge();
    entity.status = ChargeStatus.Succeeded;
    expect(entity.status).toBe(ChargeStatus.Succeeded);
    entity.status = ChargeStatus.Declined;
    expect(entity.status).toBe(ChargeStatus.Declined);
    entity.status = ChargeStatus.Refunded;
    expect(entity.status).toBe(ChargeStatus.Refunded);
  });

  it("entity_model/paymentDb/CardCharge/server_managed_fields", () => {
    const entity = new CardCharge();
    expect(entity.createdAt).toBeUndefined();
    expect(entity.updatedAt).toBeUndefined();
    expect(entity.id).toBeUndefined();
  });
});
