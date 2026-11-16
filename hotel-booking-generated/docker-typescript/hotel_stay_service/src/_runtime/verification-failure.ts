/**
 * Verification failure classification: the one mapping from a failed `jose`
 * verification to the shared-vocabulary reason code it is reported with.
 *
 * Both token validators of a generated service use it -- the identity core
 * (`_runtime/identity`) and the trusted-caller guard -- so the two classify a
 * failure identically. The guard imports only this module, never the identity core.
 *
 * Every reason code is a parameter: the importer renders each from the shared
 * vocabulary and this module never spells one.
 *
 * Shipped by cruftfree-codegen-typescript-core and emitted verbatim. Do not edit manually.
 */
import { errors as joseErrors } from 'jose';

/** The shared-vocabulary reason codes a failed token verification maps to. */
export interface VerificationFailureReasonCodes {
  readonly malformedToken: string;
  readonly expiredToken: string;
  readonly badSignature: string;
  readonly issuerMismatch: string;
  readonly audienceMismatch: string;
  readonly jwksRefreshFailed: string;
}

/**
 * The vocabulary code that classifies a failed `jose` verification.
 *
 * Claim failures are matched on the QUOTED claim name as `jose` writes it
 * (`"exp" claim timestamp check failed`, `unexpected "aud" claim value`).
 * Matching the bare claim name would misclassify: `exp` is a substring of the
 * word `unexpected` that `jose` uses, so every audience and issuer mismatch
 * would be reported as an expired token.
 *
 * A token whose `kid` names no key in the provider's key set is classified by
 * its type, before any message match: the remote key set has already re-fetched
 * the set once for the unknown `kid`, so the failure is a key-set refresh that
 * found no key (`jose` words it "no applicable key found in the JSON Web Key
 * Set", which no message branch matches).
 *
 * The code is the ONLY thing derived from the exception; its text is never
 * returned, logged as a reason or placed on a thrown error.
 */
export function classifyVerificationFailure(failure: unknown, reasons: VerificationFailureReasonCodes): string {
  if (failure instanceof joseErrors.JWKSNoMatchingKey) {
    return reasons.jwksRefreshFailed;
  }
  const message = failure instanceof Error ? failure.message : String(failure);
  if (
    message.includes('JWKS') ||
    message.includes('fetch') ||
    message.includes('network') ||
    message.includes('connect')
  ) {
    return reasons.jwksRefreshFailed;
  }
  if (message.includes('"exp"') || message.includes('expired')) {
    return reasons.expiredToken;
  }
  if (message.includes('"iss"') || message.includes('issuer')) {
    return reasons.issuerMismatch;
  }
  if (message.includes('"aud"') || message.includes('audience')) {
    return reasons.audienceMismatch;
  }
  if (message.includes('signature') || message.includes('verify') || message.includes('JWS')) {
    return reasons.badSignature;
  }
  return reasons.malformedToken;
}
