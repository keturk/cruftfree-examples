import { buildApiKey } from './api-key.factory';

describe('buildApiKey', () => {
  it("entity_factory/channelDb/ApiKey/valid_instance", () => {
    const result = buildApiKey();
    expect(result).toBeDefined();
    expect(result.keyHash).toBeDefined();
    expect(result.ownerId).toBeDefined();
    expect(result.expiresAt).toBeDefined();
    expect(result.lastUsedAt).toBeDefined();
  });

  it("entity_factory/channelDb/ApiKey/applies_overrides", () => {
    const overrides = {
      keyHash: `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`,
    };
    const result = buildApiKey(overrides);
    expect(result.keyHash).toBe(overrides.keyHash);
  });

  it("entity_factory/channelDb/ApiKey/distinct_instances", () => {
    const a = buildApiKey();
    const b = buildApiKey();
    expect(a).not.toBe(b);
  });
});
