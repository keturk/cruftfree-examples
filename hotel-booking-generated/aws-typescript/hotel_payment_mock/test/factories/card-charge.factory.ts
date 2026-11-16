import { CardCharge } from '../../src/hotel_payment_mock/entities/payment_db/card-charge.entity';
import { ChargeStatus } from '../../src/enums/charge-status.enum';

/**
 * Build a partial CardCharge with sensible defaults for testing.
 * Override any field via the `overrides` parameter.
 */
export function buildCardCharge(
  overrides?: Partial<CardCharge>,
): Partial<CardCharge> {
  return {
    reference: 'test',
    amount: '99.99',
    currency: 'tes',
    status: ChargeStatus.Succeeded,
    declineReason: 'test',
    chargeId: `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`,
    idempotencyKey: `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`,
    ...overrides,
  };
}
