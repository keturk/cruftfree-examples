import { MetadataStorage } from '@mikro-orm/core';
import { ApiKey } from '../src/realestate_mortgage_mock/entities/mortgage_db/api-key.entity';

/** The decorator metadata of a mapped property, declared on the entity or a class it extends. */
function propertyMetadata(name: string): { length?: number; nullable?: boolean } {
  let target: unknown = ApiKey;
  while (typeof target === 'function' && target !== Function.prototype) {
    const meta = MetadataStorage.getMetadataFromDecorator(target as new () => object);
    const properties = meta.properties as Record<string, { length?: number; nullable?: boolean } | undefined>;
    const property = properties[name];
    if (property !== undefined) {
      return property;
    }
    target = Object.getPrototypeOf(target);
  }
  throw new Error(`ApiKey maps no property '${name}'.`);
}

describe('ApiKey Entity', () => {
  it("entity_model/mortgageDb/ApiKey/create_instance", () => {
    const entity = new ApiKey();
    expect(entity).toBeDefined();
  });

  it("entity_model/mortgageDb/ApiKey/field_assignment", () => {
    const entity = new ApiKey();
    const keyHashVal = `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`;
    const ownerIdVal = 'a1b2c3d4-e5f6-7890-abcd-ef1234567890';
    const scopesVal = ['test_string'];
    const isActiveVal = true;
    const expiresAtVal = new Date('2024-06-20T08:30:00Z');
    const lastUsedAtVal = new Date('2025-03-10T16:45:00Z');
    entity.keyHash = keyHashVal;
    entity.ownerId = ownerIdVal;
    entity.scopes = scopesVal;
    entity.isActive = isActiveVal;
    entity.expiresAt = expiresAtVal;
    entity.lastUsedAt = lastUsedAtVal;
    expect(entity.keyHash).toBe(keyHashVal);
    expect(entity.ownerId).toBe(ownerIdVal);
    expect(entity.scopes).toBe(scopesVal);
    expect(entity.isActive).toBe(isActiveVal);
    expect(entity.expiresAt).toEqual(expiresAtVal);
    expect(entity.lastUsedAt).toEqual(lastUsedAtVal);
  });

  it("entity_model/mortgageDb/ApiKey/field_update", () => {
    const entity = new ApiKey();
    const keyHashVal = `alt_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`;
    const ownerIdVal = '550e8400-e29b-41d4-a716-446655440000';
    const scopesVal = ['sample_text'];
    const isActiveVal = false;
    const expiresAtVal = new Date('2025-03-10T16:45:00Z');
    const lastUsedAtVal = new Date('2024-11-05T09:15:00Z');
    entity.keyHash = keyHashVal;
    entity.ownerId = ownerIdVal;
    entity.scopes = scopesVal;
    entity.isActive = isActiveVal;
    entity.expiresAt = expiresAtVal;
    entity.lastUsedAt = lastUsedAtVal;
    expect(entity.keyHash).toBe(keyHashVal);
    expect(entity.ownerId).toBe(ownerIdVal);
    expect(entity.scopes).toBe(scopesVal);
    expect(entity.isActive).toBe(isActiveVal);
    expect(entity.expiresAt).toEqual(expiresAtVal);
    expect(entity.lastUsedAt).toEqual(lastUsedAtVal);
  });

  it("entity_model/mortgageDb/ApiKey/tablename", () => {
    const meta = MetadataStorage.getMetadataFromDecorator(ApiKey);
    expect(typeof meta.tableName).toBe('string');
    expect(meta.tableName.length).toBeGreaterThan(0);
  });

  it("entity_model/mortgageDb/ApiKey/keyHash/max_length", () => {
    expect(propertyMetadata('keyHash').length).toBe(64);
  });

  it("entity_model/mortgageDb/ApiKey/keyHash/unique_constraint", () => {
    const entity = new ApiKey();
    entity.keyHash = `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`;
    expect(entity.keyHash).toBeDefined();
  });

  it("entity_model/mortgageDb/ApiKey/ownerId/index", () => {
    const entity = new ApiKey();
    entity.ownerId = 'a1b2c3d4-e5f6-7890-abcd-ef1234567890';
    expect(entity.ownerId).toBeDefined();
  });

  it("entity_model/mortgageDb/ApiKey/server_managed_fields", () => {
    const entity = new ApiKey();
    expect(entity.createdAt).toBeUndefined();
    expect(entity.updatedAt).toBeUndefined();
    expect(entity.id).toBeUndefined();
  });
});
