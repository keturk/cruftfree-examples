import { ApiKey } from '../../src/hotel_channel_mock/entities/channel_db/api-key.entity';

/**
 * Build a partial ApiKey with sensible defaults for testing.
 * Override any field via the `overrides` parameter.
 */
export function buildApiKey(
  overrides?: Partial<ApiKey>,
): Partial<ApiKey> {
  return {
    keyHash: `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`,
    ownerId: crypto.randomUUID(),
    expiresAt: new Date('2025-01-15T12:00:00Z'),
    lastUsedAt: new Date('2025-01-15T12:00:00Z'),
    ...overrides,
  };
}
