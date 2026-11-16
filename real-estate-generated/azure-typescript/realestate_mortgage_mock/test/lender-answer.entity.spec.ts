import { MetadataStorage } from '@mikro-orm/core';
import { LenderAnswer } from '../src/realestate_mortgage_mock/entities/mortgage_db/lender-answer.entity';
import { PreapprovalDecision } from '../src/enums/preapproval-decision.enum';

/** The decorator metadata of a mapped property, declared on the entity or a class it extends. */
function propertyMetadata(name: string): { length?: number; nullable?: boolean } {
  let target: unknown = LenderAnswer;
  while (typeof target === 'function' && target !== Function.prototype) {
    const meta = MetadataStorage.getMetadataFromDecorator(target as new () => object);
    const properties = meta.properties as Record<string, { length?: number; nullable?: boolean } | undefined>;
    const property = properties[name];
    if (property !== undefined) {
      return property;
    }
    target = Object.getPrototypeOf(target);
  }
  throw new Error(`LenderAnswer maps no property '${name}'.`);
}

describe('LenderAnswer Entity', () => {
  it("entity_model/mortgageDb/LenderAnswer/create_instance", () => {
    const entity = new LenderAnswer();
    expect(entity).toBeDefined();
  });

  it("entity_model/mortgageDb/LenderAnswer/field_assignment", () => {
    const entity = new LenderAnswer();
    const applicantNameVal = 'foo_bar';
    const amountVal = '9.99';
    const decisionVal = PreapprovalDecision.Approved;
    const referenceVal = `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`;
    const idempotencyKeyVal = `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`;
    const applicantEmailVal = 'admin@test.org';
    entity.applicantName = applicantNameVal;
    entity.amount = amountVal;
    entity.decision = decisionVal;
    entity.reference = referenceVal;
    entity.idempotencyKey = idempotencyKeyVal;
    entity.applicantEmail = applicantEmailVal;
    expect(entity.applicantName).toBe(applicantNameVal);
    expect(entity.amount).toBe(amountVal);
    expect(entity.decision).toBe(decisionVal);
    expect(entity.reference).toBe(referenceVal);
    expect(entity.idempotencyKey).toBe(idempotencyKeyVal);
    expect(entity.applicantEmail).toBe(applicantEmailVal);
  });

  it("entity_model/mortgageDb/LenderAnswer/field_update", () => {
    const entity = new LenderAnswer();
    const applicantNameVal = 'test_string';
    const amountVal = '149.00';
    const decisionVal = PreapprovalDecision.Declined;
    const referenceVal = `alt_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`;
    const idempotencyKeyVal = `alt_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`;
    const applicantEmailVal = 'info@sample.net';
    entity.applicantName = applicantNameVal;
    entity.amount = amountVal;
    entity.decision = decisionVal;
    entity.reference = referenceVal;
    entity.idempotencyKey = idempotencyKeyVal;
    entity.applicantEmail = applicantEmailVal;
    expect(entity.applicantName).toBe(applicantNameVal);
    expect(entity.amount).toBe(amountVal);
    expect(entity.decision).toBe(decisionVal);
    expect(entity.reference).toBe(referenceVal);
    expect(entity.idempotencyKey).toBe(idempotencyKeyVal);
    expect(entity.applicantEmail).toBe(applicantEmailVal);
  });

  it("entity_model/mortgageDb/LenderAnswer/tablename", () => {
    const meta = MetadataStorage.getMetadataFromDecorator(LenderAnswer);
    expect(typeof meta.tableName).toBe('string');
    expect(meta.tableName.length).toBeGreaterThan(0);
  });

  it("entity_model/mortgageDb/LenderAnswer/applicantName/max_length", () => {
    expect(propertyMetadata('applicantName').length).toBe(200);
  });

  it("entity_model/mortgageDb/LenderAnswer/reference/max_length", () => {
    expect(propertyMetadata('reference').length).toBe(40);
  });

  it("entity_model/mortgageDb/LenderAnswer/idempotencyKey/max_length", () => {
    expect(propertyMetadata('idempotencyKey').length).toBe(120);
  });

  it("entity_model/mortgageDb/LenderAnswer/reference/unique_constraint", () => {
    const entity = new LenderAnswer();
    entity.reference = `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`;
    expect(entity.reference).toBeDefined();
  });

  it("entity_model/mortgageDb/LenderAnswer/idempotencyKey/unique_constraint", () => {
    const entity = new LenderAnswer();
    entity.idempotencyKey = `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`;
    expect(entity.idempotencyKey).toBeDefined();
  });

  it("entity_model/mortgageDb/LenderAnswer/decision/enum_round_trip", () => {
    const entity = new LenderAnswer();
    entity.decision = PreapprovalDecision.Approved;
    expect(entity.decision).toBe(PreapprovalDecision.Approved);
    entity.decision = PreapprovalDecision.Declined;
    expect(entity.decision).toBe(PreapprovalDecision.Declined);
  });

  it("entity_model/mortgageDb/LenderAnswer/server_managed_fields", () => {
    const entity = new LenderAnswer();
    expect(entity.createdAt).toBeUndefined();
    expect(entity.updatedAt).toBeUndefined();
    expect(entity.id).toBeUndefined();
  });
});
