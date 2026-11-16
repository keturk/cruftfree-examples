import { MetadataStorage } from '@mikro-orm/core';
import { Offer } from '../src/realestate_deal_service/entities/deal_db/offer.entity';
import { Financing } from '../src/enums/financing.enum';
import { OfferStatus } from '../src/enums/offer-status.enum';

/** The decorator metadata of a mapped property, declared on the entity or a class it extends. */
function propertyMetadata(name: string): { length?: number; nullable?: boolean } {
  let target: unknown = Offer;
  while (typeof target === 'function' && target !== Function.prototype) {
    const meta = MetadataStorage.getMetadataFromDecorator(target as new () => object);
    const properties = meta.properties as Record<string, { length?: number; nullable?: boolean } | undefined>;
    const property = properties[name];
    if (property !== undefined) {
      return property;
    }
    target = Object.getPrototypeOf(target);
  }
  throw new Error(`Offer maps no property '${name}'.`);
}

describe('Offer Entity', () => {
  it("entity_model/dealDb/Offer/create_instance", () => {
    const entity = new Offer();
    expect(entity).toBeDefined();
  });

  it("entity_model/dealDb/Offer/field_assignment", () => {
    const entity = new Offer();
    const listingTitleVal = 'sample_text';
    const buyerNameVal = 'hello';
    const amountVal = '149.00';
    const financingVal = Financing.Cash;
    const statusVal = OfferStatus.Submitted;
    const lenderReferenceVal = 'sample_text';
    const listingIdVal = '7c9e6679-7425-40de-944b-e07fc1f90ae7';
    const buyerEmailVal = 'user@example.com';
    const agentEmailVal = 'user@example.com';
    entity.listingTitle = listingTitleVal;
    entity.buyerName = buyerNameVal;
    entity.amount = amountVal;
    entity.financing = financingVal;
    entity.status = statusVal;
    entity.lenderReference = lenderReferenceVal;
    entity.listingId = listingIdVal;
    entity.buyerEmail = buyerEmailVal;
    entity.agentEmail = agentEmailVal;
    expect(entity.listingTitle).toBe(listingTitleVal);
    expect(entity.buyerName).toBe(buyerNameVal);
    expect(entity.amount).toBe(amountVal);
    expect(entity.financing).toBe(financingVal);
    expect(entity.status).toBe(statusVal);
    expect(entity.lenderReference).toBe(lenderReferenceVal);
    expect(entity.listingId).toBe(listingIdVal);
    expect(entity.buyerEmail).toBe(buyerEmailVal);
    expect(entity.agentEmail).toBe(agentEmailVal);
  });

  it("entity_model/dealDb/Offer/field_update", () => {
    const entity = new Offer();
    const listingTitleVal = 'hello';
    const buyerNameVal = 'world';
    const amountVal = '4.50';
    const financingVal = Financing.Mortgage;
    const statusVal = OfferStatus.Accepted;
    const lenderReferenceVal = 'hello';
    const listingIdVal = '6ba7b810-9dad-11d1-80b4-00c04fd430c8';
    const buyerEmailVal = 'admin@test.org';
    const agentEmailVal = 'admin@test.org';
    entity.listingTitle = listingTitleVal;
    entity.buyerName = buyerNameVal;
    entity.amount = amountVal;
    entity.financing = financingVal;
    entity.status = statusVal;
    entity.lenderReference = lenderReferenceVal;
    entity.listingId = listingIdVal;
    entity.buyerEmail = buyerEmailVal;
    entity.agentEmail = agentEmailVal;
    expect(entity.listingTitle).toBe(listingTitleVal);
    expect(entity.buyerName).toBe(buyerNameVal);
    expect(entity.amount).toBe(amountVal);
    expect(entity.financing).toBe(financingVal);
    expect(entity.status).toBe(statusVal);
    expect(entity.lenderReference).toBe(lenderReferenceVal);
    expect(entity.listingId).toBe(listingIdVal);
    expect(entity.buyerEmail).toBe(buyerEmailVal);
    expect(entity.agentEmail).toBe(agentEmailVal);
  });

  it("entity_model/dealDb/Offer/tablename", () => {
    const meta = MetadataStorage.getMetadataFromDecorator(Offer);
    expect(typeof meta.tableName).toBe('string');
    expect(meta.tableName.length).toBeGreaterThan(0);
  });

  it("entity_model/dealDb/Offer/listingTitle/max_length", () => {
    expect(propertyMetadata('listingTitle').length).toBe(200);
  });

  it("entity_model/dealDb/Offer/buyerName/max_length", () => {
    expect(propertyMetadata('buyerName').length).toBe(200);
  });

  it("entity_model/dealDb/Offer/lenderReference/max_length", () => {
    expect(propertyMetadata('lenderReference').length).toBe(40);
  });

  it("entity_model/dealDb/Offer/listingId/index", () => {
    const entity = new Offer();
    entity.listingId = '7c9e6679-7425-40de-944b-e07fc1f90ae7';
    expect(entity.listingId).toBeDefined();
  });

  it("entity_model/dealDb/Offer/buyerEmail/index", () => {
    const entity = new Offer();
    entity.buyerEmail = 'user@example.com';
    expect(entity.buyerEmail).toBeDefined();
  });

  it("entity_model/dealDb/Offer/agentEmail/index", () => {
    const entity = new Offer();
    entity.agentEmail = 'user@example.com';
    expect(entity.agentEmail).toBeDefined();
  });

  it("entity_model/dealDb/Offer/financing/enum_round_trip", () => {
    const entity = new Offer();
    entity.financing = Financing.Cash;
    expect(entity.financing).toBe(Financing.Cash);
    entity.financing = Financing.Mortgage;
    expect(entity.financing).toBe(Financing.Mortgage);
  });

  it("entity_model/dealDb/Offer/status/enum_round_trip", () => {
    const entity = new Offer();
    entity.status = OfferStatus.Submitted;
    expect(entity.status).toBe(OfferStatus.Submitted);
    entity.status = OfferStatus.Accepted;
    expect(entity.status).toBe(OfferStatus.Accepted);
    entity.status = OfferStatus.Rejected;
    expect(entity.status).toBe(OfferStatus.Rejected);
    entity.status = OfferStatus.Withdrawn;
    expect(entity.status).toBe(OfferStatus.Withdrawn);
  });

  it("entity_model/dealDb/Offer/server_managed_fields", () => {
    const entity = new Offer();
    expect(entity.createdAt).toBeUndefined();
    expect(entity.updatedAt).toBeUndefined();
    expect(entity.id).toBeUndefined();
  });
});
