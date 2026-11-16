/**
 * Jest spec of the verification failure runtime module (`src/_runtime/verification-failure.ts`).
 *
 * Each row is a failure message as `jose` (or the key-set fetch) writes it, with the
 * reason code it must be reported with. The `"exp"` rows guard the quoted-claim match:
 * `unexpected` contains `exp`, so a bare-name match would report every issuer and
 * audience mismatch as an expired token.
 *
 * Shipped by cruftfree-codegen-typescript-core and emitted verbatim. Do not edit manually.
 */
import { errors as joseErrors } from 'jose';
import { classifyVerificationFailure } from '../../src/_runtime/verification-failure';
import type { VerificationFailureReasonCodes } from '../../src/_runtime/verification-failure';

const REASONS: VerificationFailureReasonCodes = {
  malformedToken: 'test_malformed_token',
  expiredToken: 'test_expired_token',
  badSignature: 'test_bad_signature',
  issuerMismatch: 'test_issuer_mismatch',
  audienceMismatch: 'test_audience_mismatch',
  jwksRefreshFailed: 'test_jwks_refresh_failed',
};

describe('classifyVerificationFailure', () => {
  it.each([
    ['"exp" claim timestamp check failed', REASONS.expiredToken],
    ['unexpected "iss" claim value', REASONS.issuerMismatch],
    ['unexpected "aud" claim value', REASONS.audienceMismatch],
    ['signature verification failed', REASONS.badSignature],
    ['fetch failed', REASONS.jwksRefreshFailed],
    ['something else', REASONS.malformedToken],
  ])('classifies "%s"', (message, reason) => {
    expect(classifyVerificationFailure(new Error(message), REASONS)).toBe(reason);
  });

  it('classifies an unknown-kid key-set miss by its type as a key-set refresh failure', () => {
    expect(classifyVerificationFailure(new joseErrors.JWKSNoMatchingKey(), REASONS)).toBe(REASONS.jwksRefreshFailed);
  });

  it('classifies a thrown non-Error by its string form', () => {
    expect(classifyVerificationFailure('unexpected "aud" claim value', REASONS)).toBe(REASONS.audienceMismatch);
  });
});
