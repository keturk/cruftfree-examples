import { buildVendorEnvelope } from './vendor-envelope.factory';

describe('buildVendorEnvelope', () => {
  it("entity_factory/signatureDb/VendorEnvelope/valid_instance", () => {
    const result = buildVendorEnvelope();
    expect(result).toBeDefined();
    expect(result.signerName).toBeDefined();
    expect(result.documentTitle).toBeDefined();
    expect(result.settledAt).toBeDefined();
    expect(result.documentBody).toBeDefined();
    expect(result.signerEmail).toBeDefined();
    expect(result.envelopeId).toBeDefined();
    expect(result.idempotencyKey).toBeDefined();
  });

  it("entity_factory/signatureDb/VendorEnvelope/applies_overrides", () => {
    const overrides = {
      signerName: 'test',
    };
    const result = buildVendorEnvelope(overrides);
    expect(result.signerName).toBe(overrides.signerName);
  });

  it("entity_factory/signatureDb/VendorEnvelope/distinct_instances", () => {
    const a = buildVendorEnvelope();
    const b = buildVendorEnvelope();
    expect(a).not.toBe(b);
  });
});
