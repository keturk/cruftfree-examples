import { Outbound } from '../../src/hotel_email_mock/entities/email_db/outbound.entity';
import { DeliveryStatus } from '../../src/enums/delivery-status.enum';

/**
 * Build a partial Outbound with sensible defaults for testing.
 * Override any field via the `overrides` parameter.
 */
export function buildOutbound(
  overrides?: Partial<Outbound>,
): Partial<Outbound> {
  return {
    recipient: 'test',
    subject: 'test',
    body: 'test',
    status: DeliveryStatus.Delivered,
    deliveryId: `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`,
    idempotencyKey: `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`,
    ...overrides,
  };
}
