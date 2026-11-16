import { PublishedNight } from '../../src/hotel_channel_mock/entities/channel_db/published-night.entity';

/**
 * Build a partial PublishedNight with sensible defaults for testing.
 * Override any field via the `overrides` parameter.
 */
export function buildPublishedNight(
  overrides?: Partial<PublishedNight>,
): Partial<PublishedNight> {
  return {
    roomType: 'test',
    night: '2025-01-15',
    left: 42,
    nightlyRate: '99.99',
    receivedAt: new Date('2025-01-15T12:00:00Z'),
    ...overrides,
  };
}
