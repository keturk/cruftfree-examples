import { MetadataStorage } from '@mikro-orm/core';
import { Contract } from '../src/realestate_deal_service/entities/deal_db/contract.entity';
import { ContractStatus } from '../src/enums/contract-status.enum';

/** The decorator metadata of a mapped property, declared on the entity or a class it extends. */
function propertyMetadata(name: string): { length?: number; nullable?: boolean } {
  let target: unknown = Contract;
  while (typeof target === 'function' && target !== Function.prototype) {
    const meta = MetadataStorage.getMetadataFromDecorator(target as new () => object);
    const properties = meta.properties as Record<string, { length?: number; nullable?: boolean } | undefined>;
    const property = properties[name];
    if (property !== undefined) {
      return property;
    }
    target = Object.getPrototypeOf(target);
  }
  throw new Error(`Contract maps no property '${name}'.`);
}

describe('Contract Entity', () => {
  it("entity_model/dealDb/Contract/create_instance", () => {
    const entity = new Contract();
    expect(entity).toBeDefined();
  });

  it("entity_model/dealDb/Contract/field_assignment", () => {
    const entity = new Contract();
    const listingTitleVal = 'world';
    const buyerNameVal = 'hello';
    const priceVal = '4.50';
    const statusVal = ContractStatus.AwaitingSignature;
    const signedAtVal = new Date('2025-03-10T16:45:00Z');
    const envelopeIdVal = 'test_string';
    const listingIdVal = '7c9e6679-7425-40de-944b-e07fc1f90ae7';
    const offerIdVal = '550e8400-e29b-41d4-a716-446655440000';
    const buyerEmailVal = 'admin@test.org';
    const agentEmailVal = 'hello@world.com';
    entity.listingTitle = listingTitleVal;
    entity.buyerName = buyerNameVal;
    entity.price = priceVal;
    entity.status = statusVal;
    entity.signedAt = signedAtVal;
    entity.envelopeId = envelopeIdVal;
    entity.listingId = listingIdVal;
    entity.offerId = offerIdVal;
    entity.buyerEmail = buyerEmailVal;
    entity.agentEmail = agentEmailVal;
    expect(entity.listingTitle).toBe(listingTitleVal);
    expect(entity.buyerName).toBe(buyerNameVal);
    expect(entity.price).toBe(priceVal);
    expect(entity.status).toBe(statusVal);
    expect(entity.signedAt).toEqual(signedAtVal);
    expect(entity.envelopeId).toBe(envelopeIdVal);
    expect(entity.listingId).toBe(listingIdVal);
    expect(entity.offerId).toBe(offerIdVal);
    expect(entity.buyerEmail).toBe(buyerEmailVal);
    expect(entity.agentEmail).toBe(agentEmailVal);
  });

  it("entity_model/dealDb/Contract/field_update", () => {
    const entity = new Contract();
    const listingTitleVal = 'foo_bar';
    const buyerNameVal = 'world';
    const priceVal = '19.99';
    const statusVal = ContractStatus.Signed;
    const signedAtVal = new Date('2024-11-05T09:15:00Z');
    const envelopeIdVal = 'sample_text';
    const listingIdVal = 'a1b2c3d4-e5f6-7890-abcd-ef1234567890';
    const offerIdVal = 'cc10e5a6-b1ad-40ec-a1a3-0888c6df5738';
    const buyerEmailVal = 'info@sample.net';
    const agentEmailVal = 'user@example.com';
    entity.listingTitle = listingTitleVal;
    entity.buyerName = buyerNameVal;
    entity.price = priceVal;
    entity.status = statusVal;
    entity.signedAt = signedAtVal;
    entity.envelopeId = envelopeIdVal;
    entity.listingId = listingIdVal;
    entity.offerId = offerIdVal;
    entity.buyerEmail = buyerEmailVal;
    entity.agentEmail = agentEmailVal;
    expect(entity.listingTitle).toBe(listingTitleVal);
    expect(entity.buyerName).toBe(buyerNameVal);
    expect(entity.price).toBe(priceVal);
    expect(entity.status).toBe(statusVal);
    expect(entity.signedAt).toEqual(signedAtVal);
    expect(entity.envelopeId).toBe(envelopeIdVal);
    expect(entity.listingId).toBe(listingIdVal);
    expect(entity.offerId).toBe(offerIdVal);
    expect(entity.buyerEmail).toBe(buyerEmailVal);
    expect(entity.agentEmail).toBe(agentEmailVal);
  });

  it("entity_model/dealDb/Contract/tablename", () => {
    const meta = MetadataStorage.getMetadataFromDecorator(Contract);
    expect(typeof meta.tableName).toBe('string');
    expect(meta.tableName.length).toBeGreaterThan(0);
  });

  it("entity_model/dealDb/Contract/listingTitle/max_length", () => {
    expect(propertyMetadata('listingTitle').length).toBe(200);
  });

  it("entity_model/dealDb/Contract/buyerName/max_length", () => {
    expect(propertyMetadata('buyerName').length).toBe(200);
  });

  it("entity_model/dealDb/Contract/envelopeId/max_length", () => {
    expect(propertyMetadata('envelopeId').length).toBe(40);
  });

  it("entity_model/dealDb/Contract/listingId/unique_constraint", () => {
    const entity = new Contract();
    entity.listingId = '7c9e6679-7425-40de-944b-e07fc1f90ae7';
    expect(entity.listingId).toBeDefined();
  });

  it("entity_model/dealDb/Contract/buyerEmail/index", () => {
    const entity = new Contract();
    entity.buyerEmail = 'admin@test.org';
    expect(entity.buyerEmail).toBeDefined();
  });

  it("entity_model/dealDb/Contract/agentEmail/index", () => {
    const entity = new Contract();
    entity.agentEmail = 'hello@world.com';
    expect(entity.agentEmail).toBeDefined();
  });

  it("entity_model/dealDb/Contract/status/enum_round_trip", () => {
    const entity = new Contract();
    entity.status = ContractStatus.AwaitingSignature;
    expect(entity.status).toBe(ContractStatus.AwaitingSignature);
    entity.status = ContractStatus.Signed;
    expect(entity.status).toBe(ContractStatus.Signed);
    entity.status = ContractStatus.Declined;
    expect(entity.status).toBe(ContractStatus.Declined);
  });

  it("entity_model/dealDb/Contract/server_managed_fields", () => {
    const entity = new Contract();
    expect(entity.createdAt).toBeUndefined();
    expect(entity.updatedAt).toBeUndefined();
    expect(entity.id).toBeUndefined();
  });
});
