import { VendorEnvelope } from '../../src/realestate_signature_mock/entities/signature_db/vendor-envelope.entity';

/**
 * Build a partial VendorEnvelope with sensible defaults for testing.
 * Override any field via the `overrides` parameter.
 */
export function buildVendorEnvelope(
  overrides?: Partial<VendorEnvelope>,
): Partial<VendorEnvelope> {
  return {
    signerName: 'test',
    documentTitle: 'test',
    settledAt: new Date('2025-01-15T12:00:00Z'),
    documentBody: 'test',
    signerEmail: 'user@example.com',
    envelopeId: `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`,
    idempotencyKey: `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`,
    ...overrides,
  };
}
