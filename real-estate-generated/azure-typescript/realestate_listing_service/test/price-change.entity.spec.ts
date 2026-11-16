import { MetadataStorage } from '@mikro-orm/core';
import { PriceChange } from '../src/realestate_listing_service/entities/listing_db/price-change.entity';

describe('PriceChange Entity', () => {
  it("entity_model/listingDb/PriceChange/create_instance", () => {
    const entity = new PriceChange();
    expect(entity).toBeDefined();
  });

  it("entity_model/listingDb/PriceChange/field_assignment", () => {
    const entity = new PriceChange();
    const listingIdVal = 'f47ac10b-58cc-4372-a567-0e02b2c3d479';
    const oldPriceVal = '4.50';
    const newPriceVal = '149.00';
    entity.listingId = listingIdVal;
    entity.oldPrice = oldPriceVal;
    entity.newPrice = newPriceVal;
    expect(entity.listingId).toBe(listingIdVal);
    expect(entity.oldPrice).toBe(oldPriceVal);
    expect(entity.newPrice).toBe(newPriceVal);
  });


  it("entity_model/listingDb/PriceChange/tablename", () => {
    const meta = MetadataStorage.getMetadataFromDecorator(PriceChange);
    expect(typeof meta.tableName).toBe('string');
    expect(meta.tableName.length).toBeGreaterThan(0);
  });

  it("entity_model/listingDb/PriceChange/listingId/index", () => {
    const entity = new PriceChange();
    entity.listingId = 'f47ac10b-58cc-4372-a567-0e02b2c3d479';
    expect(entity.listingId).toBeDefined();
  });

  it("entity_model/listingDb/PriceChange/server_managed_fields", () => {
    const entity = new PriceChange();
    expect(entity.createdAt).toBeUndefined();
    expect(entity.updatedAt).toBeUndefined();
    expect(entity.id).toBeUndefined();
  });
});
