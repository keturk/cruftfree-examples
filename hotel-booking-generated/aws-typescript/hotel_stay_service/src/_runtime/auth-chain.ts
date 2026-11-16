/**
 * Authentication chain core: the bearer and API-key authentication, provider
 * allow-list and role checks every authenticated entrypoint of a service runs
 * (the REST AuthGuard, the container serverless HTTP app, the cloud serverless
 * HTTP adapters, and every websocket_api / GraphQL subscription handshake).
 *
 * authenticateToken  -> 401 on an invalid token; a revoked token is 401 and an
 *   undeterminable revocation status 503; projects the local profile for a
 *   projected-mode provider (403 when it cannot) and runs the app-owned identity
 *   write-back. Every handshake calls it with the credential it read.
 * authenticateBearer -> parses the `Authorization` header (401 when missing or
 *   malformed) and delegates to authenticateToken.
 * authenticateOptionalBearer -> `auth(optional)`: an absent header is an
 *   anonymous request (undefined); a presented one runs authenticateBearer.
 * authenticateRouteRequest -> the one bearer-or-API-key decision of a request
 *   to a route: a presented header of an API-key provider the route admits is
 *   resolved by resolveApiKeyPrincipal, and that outcome is final; otherwise the
 *   bearer chain runs.
 * resolveApiKeyPrincipal -> the one API-key entry point: an ambiguous
 *   credential or an out-of-bounds key is 401 with no network call; the key is
 *   hashed and only its hash is verified; invalid -> 401, rate-limited -> 429,
 *   verification unavailable -> 503.
 * authenticateRouteApiKey -> the API-key principal of a request to a route
 *   (undefined when no admitted key header is presented); the REST AuthGuard
 *   resolves a key here, in the same stage as the bearer chain.
 * authenticateOptionalRouteRequest -> `auth(optional)` over a route's request:
 *   nothing presented is anonymous (undefined); anything presented runs
 *   authenticateRouteRequest, so a failing credential is a 401.
 * requireProviders   -> 403 when the verified principal's provider is not in
 *   the route's allow-list.
 * requireRoles       -> 403 when the principal holds none of the route's roles
 *   (flat any-of, no role hierarchy).
 * requirePrincipalTypes -> 403 when the principal's type is not admitted.
 * bearerTokenOrForbidden -> the principal's forwardable bearer token, or 403
 *   when it holds none (an API-key principal).
 *
 * Reason codes are logged server-side only; callers return opaque bodies.
 *
 * Every project-specific value (the shared-vocabulary reason codes, the identity
 * core's verifier, the problem families, the profile store, the revocation check,
 * the API-key providers and their verifier, the write-back calls, the logger) is a
 * parameter of `createAuthChain`; the service's `auth/auth-chain.ts` binding passes
 * them. A capability the service does not realize is passed as `null`.
 *
 * Shipped by cruftfree-codegen-typescript-core and emitted verbatim. Do not edit manually.
 */
import { ForbiddenException } from '@nestjs/common';
import { createHash } from 'node:crypto';
import { IdentityVerificationError } from './identity';
import type { IdentityPrincipalOf, IdentityProfileDocument } from './identity';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/** The header a bearer token is presented in. */
const AUTHORIZATION_HEADER = 'authorization';
/** The local identity mode whose principal resolves its user id through the profile store. */
const PROJECTED_IDENTITY_MODE = 'projected';
/** The owner id a verified key carries is already a resolved local user id. */
const API_KEY_LOCAL_IDENTITY_MODE = 'subjectText';
const MILLISECONDS_PER_SECOND = 1000;

/** Log-only reason codes of a refused API key -- never returned to the caller. */
export const REASON_API_KEY_AMBIGUOUS = 'ambiguous_credentials';
const REASON_API_KEY_OUT_OF_BOUNDS = 'api_key_out_of_bounds';
const REASON_API_KEY_INVALID = 'api_key_invalid';
const REASON_API_KEY_RATE_LIMITED = 'api_key_rate_limited';
const REASON_API_KEY_VERIFIER_UNAVAILABLE = 'api_key_verifier_unavailable';

const ISO_DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/;
const PLAIN_DECIMAL_PATTERN = /^-?\d+(\.\d+)?$/;

// ---------------------------------------------------------------------------
// Failed steps and the refusal shape
// ---------------------------------------------------------------------------

/**
 * The status of a failed auth-chain step: 401 (authentication), 403
 * (authorization), 429 (a rate-limited API key) or 503 (an API key whose
 * verification could not complete, or a credential whose revocation status
 * could not be determined -- fail closed).
 */
export type AuthChainStatus = 401 | 403 | 429 | 503;

/** A failed auth-chain step, carrying the status every caller answers with. */
export class AuthChainError extends Error {
  constructor(
    readonly status: AuthChainStatus,
    readonly reasonCode: string,
  ) {
    super(reasonCode);
    this.name = 'AuthChainError';
  }
}

/**
 * A credential whose revocation status could not be determined: 503, never an allow and never a
 * 401 (the credential may be valid, and a 401 would send clients into re-login loops that cannot
 * succeed while the store is down). Answered as the registered revocation-unavailable problem
 * family with `Retry-After`.
 */
export class AuthChainRevocationUnavailableError extends AuthChainError {
  constructor(
    reasonCode: string,
    readonly retryAfterSeconds: number,
  ) {
    super(503, reasonCode);
    this.name = 'AuthChainRevocationUnavailableError';
  }
}

/** A rate-limited API key: 429, told when to come back through `Retry-After`. */
export class AuthChainRateLimitedError extends AuthChainError {
  constructor(
    reasonCode: string,
    readonly retryAfterSeconds: number,
  ) {
    super(429, reasonCode);
    this.name = 'AuthChainRateLimitedError';
  }
}

/** The opaque detail every non-Nest entrypoint answers a failed step with, by status. */
const FAILURE_DETAILS: Readonly<Record<AuthChainStatus, string>> = {
  401: 'Authentication required',
  403: 'Insufficient permissions',
  429: 'Too many requests',
  503: 'Service temporarily unavailable',
};

/** The opaque response detail of a failed step -- never its reason code. */
export function authChainFailureDetail(err: AuthChainError): string {
  return FAILURE_DETAILS[err.status];
}

/**
 * The response headers a failed step answers with: `Retry-After` for a rate-limited key and for a
 * credential whose revocation status could not be determined.
 */
export function authChainFailureHeaders(err: AuthChainError): Record<string, string> {
  return err instanceof AuthChainRateLimitedError || err instanceof AuthChainRevocationUnavailableError
    ? { 'Retry-After': String(err.retryAfterSeconds) }
    : {};
}

// ---------------------------------------------------------------------------
// Request headers
// ---------------------------------------------------------------------------

/**
 * Request headers as every entrypoint holds them: Node's lower-cased
 * `IncomingHttpHeaders`, a Lambda proxy event's caller-cased map, or the
 * entries of a Fetch `Headers`. Every read below is case-insensitive.
 */
export type RequestHeaders = Readonly<Record<string, string | ReadonlyArray<string> | undefined>>;

/** Every value of header *name* in *headers*, whatever its casing. */
function headerValues(headers: RequestHeaders, name: string): string[] {
  const wanted = name.toLowerCase();
  const values: string[] = [];
  for (const [key, value] of Object.entries(headers)) {
    if (key.toLowerCase() !== wanted || value === undefined) {
      continue;
    }
    if (typeof value === 'string') {
      values.push(value);
    } else {
      values.push(...value);
    }
  }
  return values;
}

/**
 * The single value of header *name*; two differing copies are ambiguous and
 * yield none, so the chain denies instead of picking one.
 */
function singleHeaderValue(headers: RequestHeaders, name: string): string | undefined {
  const distinct = new Set(headerValues(headers, name));
  return distinct.size === 1 ? [...distinct][0] : undefined;
}

function bearerToken(authorization: string | undefined | null): string | undefined {
  if (!authorization) {
    return undefined;
  }
  const [type, value] = authorization.split(' ');
  return type === 'Bearer' && value ? value : undefined;
}

// ---------------------------------------------------------------------------
// Identity write-back serialization
// ---------------------------------------------------------------------------

/**
 * How a write-back field's value becomes claim text -- decided at GENERATION
 * time from the field's declared DSL type, never by a generic `String(value)`.
 */
export type WriteBackValueKind = 'text' | 'enum' | 'uuid' | 'date' | 'date_time' | 'decimal' | 'integer' | 'boolean';

/**
 * One app-owned identity write-back call, baked at GENERATION time from the
 * resolved `.ccfg` (never resolved at runtime). One entry per (provider, field)
 * pair; `provider` selects which entries apply to a given validated token via
 * `principal.provider`.
 */
export interface WriteBackCall {
  readonly provider: string;
  readonly entity: string;
  readonly keyField: string;
  readonly field: string;
  readonly valueKind: WriteBackValueKind;
  /**
   * The field is this service's tenant identifier: the row, its source of truth,
   * names the principal's tenant (never the token's converging claim copy).
   */
  readonly attributesTenant: boolean;
}

/**
 * Plain positional decimal text: no exponent, trailing fractional zeros and a
 * bare trailing point removed, negative zero as `0`.
 */
function canonicalDecimalText(value: unknown): string {
  const raw =
    typeof value === 'number'
      ? value.toLocaleString('en-US', { useGrouping: false, maximumFractionDigits: 20 })
      : String(value);
  if (!PLAIN_DECIMAL_PATTERN.test(raw)) {
    throw new Error(
      'Identity write-back cannot serialize a decimal field value: it is not a ' +
        'plain decimal number. Expected digits with an optional sign and fraction.',
    );
  }
  const trimmed = raw.includes('.') ? raw.replace(/0+$/, '').replace(/\.$/, '') : raw;
  return trimmed === '-0' ? '0' : trimmed;
}

/**
 * The claim text for a write-back field value, by the field's declared kind.
 * Every language's write-back seam produces the same canonical text per kind.
 */
export function writeBackText(value: unknown, kind: WriteBackValueKind): string {
  switch (kind) {
    case 'text':
      return String(value);
    case 'enum':
      // A generated string enum member is its value.
      return String(value);
    case 'uuid':
      return String(value).toLowerCase();
    case 'date': {
      if (value instanceof Date) {
        return value.toISOString().slice(0, 10);
      }
      const text = String(value);
      if (!ISO_DATE_PATTERN.test(text)) {
        throw new Error(
          'Identity write-back cannot serialize a date field value: expected an ' +
            'ISO 8601 calendar date (YYYY-MM-DD).',
        );
      }
      return text;
    }
    case 'date_time':
      return (value instanceof Date ? value : new Date(String(value))).toISOString();
    case 'decimal':
      return canonicalDecimalText(value);
    case 'integer':
      return String(value);
    case 'boolean':
      return value ? 'true' : 'false';
    default: {
      const unhandled: never = kind;
      throw new Error(`Identity write-back has no serialization for value kind '${String(unhandled)}'.`);
    }
  }
}

// ---------------------------------------------------------------------------
// Parameters
// ---------------------------------------------------------------------------

/**
 * The shared-vocabulary reason codes the chain refuses with. The binding renders
 * each from the vocabulary; this module never spells one.
 */
export interface AuthChainReasonCodes {
  readonly missingToken: string;
  readonly providerNotAllowed: string;
  readonly roleDenied: string;
  readonly principalTypeMismatch: string;
  readonly profileUnavailable: string;
  readonly providerConfigError: string;
  readonly noForwardableToken: string;
}

/** Where this module's log lines go (the service's framework logger). */
export interface AuthChainLogger {
  log(message: string): void;
  warn(message: string): void;
  error(message: string, stack?: string): void;
  debug(message: string): void;
}

/** The problem bodies a non-Nest entrypoint answers a failed step with. */
export interface AuthChainProblems<TProblem> {
  /** The registered revocation-unavailable problem family's body for `instance`. */
  readonly revocationUnavailable: (instance: string) => TProblem;
  /** The generic problem family of `status`, with the opaque `detail`. */
  readonly forStatus: (status: AuthChainStatus, instance: string, detail: string) => TProblem;
}

/** An error class whose instances carry a shared-vocabulary reason code. */
export type ReasonCodedErrorClass = abstract new (...args: never[]) => Error & { readonly reasonCode: string };

/** The revocation check of a service that realizes revocation. */
export interface AuthChainRevocation<TProfile extends IdentityProfileDocument> {
  /** Resolves when the verified credential is not revoked; throws one of the two errors below otherwise. */
  readonly assertNotRevoked: (principal: IdentityPrincipalOf<TProfile>, token: string) => Promise<void>;
  /** The credential is revoked, outlives the declared window, or contradicts introspection (401). */
  readonly refusedError: ReasonCodedErrorClass;
  /** The revocation status could not be determined (503). */
  readonly unavailableError: ReasonCodedErrorClass;
  /** The `Retry-After` an undeterminable revocation status answers with. */
  readonly retryAfterSeconds: number;
}

/** One API-key provider some surface of this service admits. */
export interface AdmittedApiKeyProvider {
  /** The provider's name. */
  readonly name: string;
  /** The request header the key is read from, lower-cased. */
  readonly header: string;
  /** Scope -> role; an unmapped scope grants nothing. */
  readonly roleMappings: Readonly<Record<string, string>>;
}

/** Presented-key bounds, checked before the key is hashed and before any network call. */
export interface ApiKeyBounds {
  readonly minLength: number;
  readonly maxLength: number;
  /** The lowest character code a key may carry. */
  readonly minCharCode: number;
  /** The highest character code a key may carry. */
  readonly maxCharCode: number;
}

/** The store's verdict on a presented key hash. An invalid key carries no cause. */
export type ApiKeyOutcome =
  | {
      readonly outcome: 'ok';
      readonly keyId: string;
      readonly ownerId: string;
      readonly tenantId: string | null;
      readonly scopes: ReadonlyArray<string>;
      readonly expiresAt: string | null;
    }
  | { readonly outcome: 'invalid' }
  | { readonly outcome: 'rateLimited'; readonly retryAfterSeconds: number };

/** The API-key credential chain of a service some surface of which admits an API-key provider. */
export interface AuthChainApiKeys {
  /** Every API-key provider some surface of this service admits, in declaration order. */
  readonly providers: ReadonlyArray<AdmittedApiKeyProvider>;
  /** The principal type of every API-key principal: a key acts for its human owner. */
  readonly principalType: string;
  readonly keyBounds: ApiKeyBounds;
  /** Verify a presented key's hash -- in-process or through the key store's verify route. */
  readonly verifyPresentedKeyHash: (provider: string, keyHash: string) => Promise<ApiKeyOutcome>;
  /** The error `verifyPresentedKeyHash` throws when verification cannot complete (503). */
  readonly verifierUnavailableError: abstract new (...args: never[]) => Error;
}

/** One unit of work on the profile store the write-back reads an app-owned field from. */
export interface WriteBackStore {
  findOne(entityName: string, where: Record<string, string>): Promise<object | null>;
}

/** The app-owned identity write-back of a service that realizes one. */
export interface AuthChainWriteBack {
  readonly calls: ReadonlyArray<WriteBackCall>;
  /**
   * The platform-declared provider subject claim the write-back call
   * authenticates against -- never `principal.sub` unconditionally.
   */
  readonly subjectClaim: string;
  /** A fresh unit of work on the bound profile store, or null when no store is bound. */
  readonly openStore: () => WriteBackStore | null;
  /**
   * Push one field's claim text to the identity provider's management API (never throws).
   * `provider` names the provider the user signed in at: a platform that holds each provider's
   * users apart addresses that provider's users with it.
   */
  readonly writeUserMetadata: (
    provider: string,
    providerSubject: string,
    key: string,
    value: string,
  ) => Promise<void>;
}

/** Everything project-specific the auth chain needs, passed by the service's binding. */
export interface AuthChainOptions<TProfile extends IdentityProfileDocument, TProblem> {
  readonly reasons: AuthChainReasonCodes;
  /** The identity core's token verification. */
  readonly verifyIdentityToken: (token: string) => Promise<IdentityPrincipalOf<TProfile>>;
  readonly problems: AuthChainProblems<TProblem>;
  /**
   * The profile projection of a service with a projected-mode provider; null when no
   * provider resolves to projected mode, so a projected principal is always denied.
   */
  readonly loadIdentityProfile: ((principal: IdentityPrincipalOf<TProfile>) => Promise<TProfile | null>) | null;
  /** The revocation check; null when the service realizes no revocation. */
  readonly revocation: AuthChainRevocation<TProfile> | null;
  /** The API-key chain; null when no surface of the service admits an API-key provider. */
  readonly apiKeys: AuthChainApiKeys | null;
  /** The identity write-back; null when the service realizes none. */
  readonly writeBack: AuthChainWriteBack | null;
  readonly logger: AuthChainLogger;
}

// ---------------------------------------------------------------------------
// The auth chain of one service
// ---------------------------------------------------------------------------

/** The authentication operations a service's binding exports. */
export interface AuthChain<TProfile extends IdentityProfileDocument, TProblem> {
  /**
   * The problem body a non-Nest entrypoint (the serverless adapters, the gateway verify endpoint)
   * answers a failed step with: the registered revocation-unavailable family for an undeterminable
   * revocation status, the generic family of the status otherwise. Opaque: never the reason code.
   */
  readonly authChainProblemBody: (err: AuthChainError, instance: string) => TProblem;
  /**
   * Verify the bearer token of an `Authorization` header value (may be absent).
   *
   * @throws AuthChainError 401 for a missing/invalid token; 403 when a
   *   projected-mode principal's profile cannot be resolved.
   */
  readonly authenticateBearer: (authorization: string | undefined | null) => Promise<IdentityPrincipalOf<TProfile>>;
  /**
   * `auth(optional)`: an absent `Authorization` header is an anonymous request
   * (`undefined`); a presented one runs the full bearer chain, so a credential
   * that fails verification is a 401, never an anonymous request.
   */
  readonly authenticateOptionalBearer: (
    authorization: string | undefined | null,
  ) => Promise<IdentityPrincipalOf<TProfile> | undefined>;
  /**
   * Verify a credential, already extracted from its source, and resolve the application principal.
   *
   * @throws AuthChainError 401 for an invalid or revoked token; 503 when its revocation
   *   status cannot be determined; 403 when a projected-mode principal's profile cannot be
   *   resolved.
   */
  readonly authenticateToken: (token: string) => Promise<IdentityPrincipalOf<TProfile>>;
  /**
   * The bearer token a principal was authenticated with.
   *
   * @throws ForbiddenException when the principal carries no forwardable token.
   */
  readonly bearerTokenOrForbidden: (principal: IdentityPrincipalOf<TProfile>) => string;
  /**
   * Authenticate one request to a route: the single bearer-or-API-key decision.
   *
   * @throws AuthChainError with the status the caller answers with.
   */
  readonly authenticateRouteRequest: (
    headers: RequestHeaders,
    admittedApiKeyProviders: ReadonlyArray<string>,
  ) => Promise<IdentityPrincipalOf<TProfile>>;
  /**
   * `auth(optional)` over a route's request: nothing presented is anonymous (`undefined`).
   *
   * @throws AuthChainError with the status the caller answers with.
   */
  readonly authenticateOptionalRouteRequest: (
    headers: RequestHeaders,
    admittedApiKeyProviders: ReadonlyArray<string>,
  ) => Promise<IdentityPrincipalOf<TProfile> | undefined>;
  /** True when *headers* carry the header of any provider in *admittedProviders*. */
  readonly hasAdmittedApiKeyHeader: (headers: RequestHeaders, admittedProviders: ReadonlyArray<string>) => boolean;
  /**
   * Resolve the API-key principal of a request.
   *
   * @throws AuthChainError 401 for no admitted key, ambiguous credentials, an
   *   out-of-bounds key or a key the store refuses; AuthChainRateLimitedError
   *   (429) for a rate-limited key; AuthChainError 503 when verification cannot
   *   complete.
   */
  readonly resolveApiKeyPrincipal: (
    headers: RequestHeaders,
    admittedProviders: ReadonlyArray<string>,
  ) => Promise<IdentityPrincipalOf<TProfile>>;
  /** The API-key providers among a route's provider allow-list, in declaration order. */
  readonly routeApiKeyProviders: (routeProviders: ReadonlyArray<string>) => string[];
  /**
   * True when the request presents the header of an API-key provider the route
   * admits. Reads only header presence -- no key is hashed or verified.
   */
  readonly presentsRouteApiKey: (headers: RequestHeaders, routeProviders: ReadonlyArray<string>) => boolean;
  /**
   * The API-key principal of a request to a route, or `undefined` when the
   * request presents no key for a provider the route admits.
   *
   * @throws AuthChainError as `resolveApiKeyPrincipal` does.
   */
  readonly authenticateRouteApiKey: (
    headers: RequestHeaders,
    routeProviders: ReadonlyArray<string>,
  ) => Promise<IdentityPrincipalOf<TProfile> | undefined>;
  /** @throws AuthChainError 403 when the principal's provider is not in `allowed`. */
  readonly requireProviders: (principal: IdentityPrincipalOf<TProfile>, allowed: ReadonlyArray<string>) => void;
  /** @throws AuthChainError 403 when the principal holds none of `required` (flat any-of). */
  readonly requireRoles: (principal: IdentityPrincipalOf<TProfile>, required: ReadonlyArray<string>) => void;
  /** @throws AuthChainError 403 when the principal's type is not in `allowed`. */
  readonly requirePrincipalTypes: (principal: IdentityPrincipalOf<TProfile>, allowed: ReadonlyArray<string>) => void;
}

/** The auth chain of one service, over the identity core, stores and verifiers its binding passes. */
export function createAuthChain<TProfile extends IdentityProfileDocument, TProblem>(
  chainOptions: AuthChainOptions<TProfile, TProblem>,
): AuthChain<TProfile, TProblem> {
  type Principal = IdentityPrincipalOf<TProfile>;

  const LOGGER = chainOptions.logger;
  const REASONS = chainOptions.reasons;
  const PROBLEMS = chainOptions.problems;
  const LOAD_IDENTITY_PROFILE = chainOptions.loadIdentityProfile;
  const REVOCATION = chainOptions.revocation;
  const API_KEYS = chainOptions.apiKeys;
  const WRITE_BACK = chainOptions.writeBack;
  const API_KEY_PROVIDERS: ReadonlyMap<string, AdmittedApiKeyProvider> = new Map(
    (API_KEYS === null ? [] : API_KEYS.providers).map((provider): [string, AdmittedApiKeyProvider] => [
      provider.name,
      provider,
    ]),
  );

  function authChainProblemBody(err: AuthChainError, instance: string): TProblem {
    if (err instanceof AuthChainRevocationUnavailableError) {
      return PROBLEMS.revocationUnavailable(instance);
    }
    return PROBLEMS.forStatus(err.status, instance, authChainFailureDetail(err));
  }

  /**
   * The vocabulary code of a failed verification.
   *
   * A typed `IdentityVerificationError` carries its code. Any other error is a
   * deployment or configuration defect (an unreadable plan, an unset audience
   * ref) -- it is refused like any failed credential (401) under the
   * provider-config-error code and logged as a configuration error, never
   * mistaken for a token failure and never allowed.
   */
  function reasonOf(err: unknown): string {
    if (err instanceof IdentityVerificationError) {
      return err.reasonCode;
    }
    LOGGER.error(
      `identity_auth_config_error reason_code=${REASONS.providerConfigError}`,
      err instanceof Error ? err.stack : undefined,
    );
    return REASONS.providerConfigError;
  }

  async function authenticateBearer(authorization: string | undefined | null): Promise<Principal> {
    const token = bearerToken(authorization);
    if (token === undefined) {
      LOGGER.warn(`identity_auth_failed reason_code=${REASONS.missingToken}`);
      throw new AuthChainError(401, REASONS.missingToken);
    }
    return authenticateToken(token);
  }

  async function authenticateOptionalBearer(authorization: string | undefined | null): Promise<Principal | undefined> {
    if (authorization === undefined || authorization === null) {
      return undefined;
    }
    return authenticateBearer(authorization);
  }

  /**
   * Revocation: after verification, before projection and write-back, so a revoked token never
   * upserts a profile or writes back a claim. A provider whose mode is `none` pays nothing. A
   * status that cannot be determined is a 503 -- never "not revoked".
   */
  async function assertNotRevoked(revocation: AuthChainRevocation<TProfile>, principal: Principal, token: string): Promise<void> {
    try {
      await revocation.assertNotRevoked(principal, token);
    } catch (err) {
      if (err instanceof revocation.refusedError) {
        LOGGER.warn(`identity_auth_failed reason_code=${err.reasonCode} provider=${principal.provider}`);
        throw new AuthChainError(401, err.reasonCode);
      }
      if (err instanceof revocation.unavailableError) {
        LOGGER.warn(`identity_auth_failed reason_code=${err.reasonCode} provider=${principal.provider}`);
        throw new AuthChainRevocationUnavailableError(err.reasonCode, revocation.retryAfterSeconds);
      }
      throw err;
    }
  }

  /**
   * The projected principal with its profile: `userId` becomes the profile id. A profile that
   * cannot be resolved -- or a service that emits no profile store, where a projected principal
   * can never be resolved -- is denied (403) rather than passed through with an empty user id.
   */
  async function withProjectedProfile(principal: Principal): Promise<Principal> {
    const profile = LOAD_IDENTITY_PROFILE === null ? null : await LOAD_IDENTITY_PROFILE(principal);
    if (profile === null) {
      LOGGER.warn(`identity_auth_failed reason_code=${REASONS.profileUnavailable} provider=${principal.provider}`);
      throw new AuthChainError(403, REASONS.profileUnavailable);
    }
    return { ...principal, userId: profile.profileId, profile };
  }

  /**
   * Push each app-owned field's CURRENT value to the identity provider's
   * management API. Resolution (gate, platform declaration, the binding's
   * render context) happened at GENERATION time; this function only performs
   * the per-request entity read + the fail-soft write client call.
   *
   * Convergence note: the value written here lands on the NEXT token issued
   * for this user, not the one being minted -- the provider stamps the
   * claim from the metadata written during THIS authentication.
   *
   * Unclaimed-row note: the read is keyed on the author-declared key column,
   * NOT necessarily the primary key -- under `deterministicUuid5` the
   * resolved id is a stateless uuid5, not a stored PK. A pre-created member
   * whose key column is still NULL on their first authentication matches no
   * row here, so nothing is written this time.
   *
   * @returns The tenant the row of the call that attributes it names (its
   *   canonical text), or `null` when no call attributes the tenant, the caller
   *   has no row, or the row names none.
   */
  async function performIdentityWriteBack(
    writeBack: AuthChainWriteBack,
    principal: Principal,
    calls: ReadonlyArray<WriteBackCall>,
  ): Promise<string | null> {
    const store = writeBack.openStore();
    if (store === null) {
      LOGGER.warn(`identity_write_back_entity_manager_unbound provider=${principal.provider}`);
      return null;
    }
    if (!principal.userId) {
      LOGGER.warn(`identity_write_back_no_resolved_id provider=${principal.provider}`);
      return null;
    }
    // The provider subject claim is PLATFORM-DECLARED, never hardcoded --
    // an absent claim is a structural deployment defect (e.g. a missing
    // scope grant), not a transient error, so it fails LOUD rather than
    // being logged and skipped.
    const claims = principal.claims as Record<string, unknown>;
    const subjectValue = claims[writeBack.subjectClaim];
    if (typeof subjectValue !== 'string' || !subjectValue) {
      throw new Error(
        `Identity write-back requires the '${writeBack.subjectClaim}' claim, but the ` +
          'verified token does not carry it. This is a structural deployment defect ' +
          "(e.g. a missing scope grant), not a transient error, and cannot self-heal -- " +
          "fix the identity provider's token configuration.",
      );
    }
    let storeTenant: string | null = null;
    for (const call of calls) {
      const row = await store.findOne(call.entity, { [call.keyField]: principal.userId });
      if (row === null) {
        continue;
      }
      const value = (row as Record<string, unknown>)[call.field];
      if (value === null || value === undefined) {
        continue;
      }
      const text = writeBackText(value, call.valueKind);
      if (call.attributesTenant) {
        storeTenant = text;
      }
      await writeBack.writeUserMetadata(principal.provider, subjectValue, call.field, text);
    }
    return storeTenant;
  }

  /** The principal after the write-back of its provider's calls; the store's tenant when a call attributes it. */
  async function withWriteBack(writeBack: AuthChainWriteBack, principal: Principal): Promise<Principal> {
    const providerCalls = writeBack.calls.filter((c) => c.provider === principal.provider);
    if (providerCalls.length === 0) {
      return principal;
    }
    const storeTenant = await performIdentityWriteBack(writeBack, principal, providerCalls);
    if (!providerCalls.some((c) => c.attributesTenant)) {
      return principal;
    }
    // The profile-store row names this principal's tenant -- none when the
    // caller has no row or the row names none (tenantFromPrincipal never reads
    // the claim for this provider).
    return { ...principal, tenantId: storeTenant };
  }

  /**
   * Every step the bearer chain runs after the credential is extracted: signature, expiry,
   * issuer, audience and algorithm (`verifyIdentityToken`), revocation, the projected-mode
   * profile lookup that turns a projected principal's empty `userId` into its profile id, and
   * the app-owned identity write-back.
   */
  async function authenticateToken(token: string): Promise<Principal> {
    let principal: Principal;
    try {
      principal = await chainOptions.verifyIdentityToken(token);
    } catch (err) {
      const reason = reasonOf(err);
      LOGGER.warn(`identity_auth_failed reason_code=${reason}`);
      throw new AuthChainError(401, reason);
    }
    if (REVOCATION !== null) {
      await assertNotRevoked(REVOCATION, principal, token);
    }
    if (principal.localIdentityMode === PROJECTED_IDENTITY_MODE) {
      principal = await withProjectedProfile(principal);
    }
    if (WRITE_BACK !== null) {
      principal = await withWriteBack(WRITE_BACK, principal);
    }
    LOGGER.debug(`identity_token_verified provider=${principal.provider}`);
    return principal;
  }

  /**
   * A JWT-authenticated principal always carries the token it was verified with.
   * A principal with no forwardable credential (an API-key principal) carries
   * `token: null` by construction -- forwarding the raw API key downstream is
   * forbidden, so this throws rather than returning anything.
   */
  function bearerTokenOrForbidden(principal: Principal): string {
    if (principal.token === null) {
      LOGGER.warn(`identity_auth_failed reason_code=${REASONS.noForwardableToken} provider=${principal.provider}`);
      throw new ForbiddenException('No forwardable credential for this principal.');
    }
    return principal.token;
  }

  /** A route admits API-key providers this service renders no chain for: a generation drift. */
  function noApiKeyChain(admittedApiKeyProviders: ReadonlyArray<string>): Error {
    return new Error(
      `A route admits the API-key providers ${admittedApiKeyProviders.join(', ')}, but this ` +
        'service renders no API-key chain. Regenerate the service so both agree.',
    );
  }

  /**
   * When the request presents the header of an API-key provider the route
   * admits, the key is resolved by resolveApiKeyPrincipal and its outcome is
   * final (401/429/503 propagate; the bearer chain never runs to report a
   * misleading missing token). Otherwise the `Authorization` bearer chain runs.
   * `admittedApiKeyProviders` is rendered per route at generation time; empty
   * for a route admitting none.
   */
  async function authenticateRouteRequest(
    headers: RequestHeaders,
    admittedApiKeyProviders: ReadonlyArray<string>,
  ): Promise<Principal> {
    if (API_KEYS === null) {
      if (admittedApiKeyProviders.length > 0) {
        throw noApiKeyChain(admittedApiKeyProviders);
      }
    } else if (hasAdmittedApiKeyHeader(headers, admittedApiKeyProviders)) {
      return resolveApiKeyPrincipal(headers, admittedApiKeyProviders);
    }
    return authenticateBearer(singleHeaderValue(headers, AUTHORIZATION_HEADER));
  }

  /**
   * No credential presented -- no `Authorization` header and no header of an
   * admitted API-key provider -- is an anonymous request (`undefined`); anything
   * presented runs authenticateRouteRequest, so a credential that fails
   * verification (or is ambiguous) is a 401, never an anonymous request.
   */
  async function authenticateOptionalRouteRequest(
    headers: RequestHeaders,
    admittedApiKeyProviders: ReadonlyArray<string>,
  ): Promise<Principal | undefined> {
    const presentsNoKey =
      API_KEYS === null
        ? admittedApiKeyProviders.length === 0
        : !hasAdmittedApiKeyHeader(headers, admittedApiKeyProviders);
    if (headerValues(headers, AUTHORIZATION_HEADER).length === 0 && presentsNoKey) {
      return undefined;
    }
    return authenticateRouteRequest(headers, admittedApiKeyProviders);
  }

  /** An admitted API-key provider; any other name is a generation drift, never a runtime input. */
  function admittedApiKeyProvider(provider: string): AdmittedApiKeyProvider {
    const admitted = API_KEY_PROVIDERS.get(provider);
    if (admitted === undefined) {
      throw new Error(
        `'${provider}' is not an API-key provider this service admits. ` +
          `Admitted providers: ${[...API_KEY_PROVIDERS.keys()].join(', ')}. Regenerate the service.`,
      );
    }
    return admitted;
  }

  function hasAdmittedApiKeyHeader(headers: RequestHeaders, admittedProviders: ReadonlyArray<string>): boolean {
    return admittedProviders.some((provider) => headerValues(headers, admittedApiKeyProvider(provider).header).length > 0);
  }

  /**
   * The provider and presented key of the one admitted key header present.
   *
   * Only the headers of *admittedProviders* are read: a key header a route does
   * not admit is ignored entirely. An `Authorization` header together with an
   * admitted key header, two admitted key headers, or one key header sent twice
   * is ambiguous and refused before any network call.
   */
  function presentedApiKey(
    headers: RequestHeaders,
    admittedProviders: ReadonlyArray<string>,
  ): { readonly provider: string; readonly presentedKey: string } {
    const presented = admittedProviders
      .map((provider) => ({
        provider,
        values: headerValues(headers, admittedApiKeyProvider(provider).header),
      }))
      .filter((candidate) => candidate.values.length > 0);
    if (presented.length === 0) {
      LOGGER.warn(`identity_auth_failed reason_code=${REASONS.missingToken}`);
      throw new AuthChainError(401, REASONS.missingToken);
    }
    const ambiguous =
      presented.length > 1 || presented[0].values.length > 1 || headerValues(headers, AUTHORIZATION_HEADER).length > 0;
    if (ambiguous) {
      LOGGER.warn(`identity_auth_failed reason_code=${REASON_API_KEY_AMBIGUOUS}`);
      throw new AuthChainError(401, REASON_API_KEY_AMBIGUOUS);
    }
    return { provider: presented[0].provider, presentedKey: presented[0].values[0] };
  }

  /** True when *presentedKey* is within *bounds*: its length, and every character code. */
  function withinKeyBounds(presentedKey: string, bounds: ApiKeyBounds): boolean {
    if (presentedKey.length === 0 || presentedKey.length < bounds.minLength || presentedKey.length > bounds.maxLength) {
      return false;
    }
    for (let index = 0; index < presentedKey.length; index += 1) {
      const code = presentedKey.charCodeAt(index);
      if (code < bounds.minCharCode || code > bounds.maxCharCode) {
        return false;
      }
    }
    return true;
  }

  /**
   * The lower-case hex SHA-256 digest of a key within the presented-key bounds.
   *
   * The only function that reads the raw key: it is bounds-checked, then
   * hashed, and only the hash ever leaves this function.
   */
  function hashPresentedKey(apiKeys: AuthChainApiKeys, provider: string, presentedKey: string): string {
    if (!withinKeyBounds(presentedKey, apiKeys.keyBounds)) {
      LOGGER.warn(`identity_auth_failed provider=${provider} reason_code=${REASON_API_KEY_OUT_OF_BOUNDS}`);
      throw new AuthChainError(401, REASON_API_KEY_OUT_OF_BOUNDS);
    }
    return createHash('sha256').update(presentedKey, 'utf8').digest('hex');
  }

  /** The roles *scopes* map to through *provider*'s mappings; unmapped scopes grant nothing. */
  function mapApiKeyScopes(provider: string, scopes: ReadonlyArray<string>): string[] {
    const mappings = admittedApiKeyProvider(provider).roleMappings;
    return scopes.flatMap((scope) => (Object.prototype.hasOwnProperty.call(mappings, scope) ? [mappings[scope]] : []));
  }

  /**
   * The one API-key entry point of every surface (the REST AuthGuard through
   * authenticateRouteApiKey, the serverless adapters, a websocket_api
   * handshake). A presented key is bounds-checked and hashed before anything
   * else; only its hash reaches the verification, which runs in-process when
   * this service stores the provider's keys and otherwise calls the store's
   * verify route once -- never retried, never cached.
   *
   * The principal is an ordinary IdentityPrincipal: `sub` is the key's id,
   * `userId` its owner, `roles` its scopes mapped through the provider's
   * mappings, `tenantId` the key's tenant, `token` null (a key is never
   * forwarded), and `claims` carries only `exp` -- the key's expiry -- so every
   * expiry-driven surface treats a key exactly like a token.
   */
  async function resolveApiKeyPrincipal(
    headers: RequestHeaders,
    admittedProviders: ReadonlyArray<string>,
  ): Promise<Principal> {
    if (API_KEYS === null) {
      throw noApiKeyChain(admittedProviders);
    }
    const { provider, presentedKey } = presentedApiKey(headers, admittedProviders);
    const keyHash = hashPresentedKey(API_KEYS, provider, presentedKey);
    let outcome: ApiKeyOutcome;
    try {
      outcome = await API_KEYS.verifyPresentedKeyHash(provider, keyHash);
    } catch (err) {
      if (err instanceof API_KEYS.verifierUnavailableError) {
        LOGGER.error(`identity_auth_failed provider=${provider} reason_code=${REASON_API_KEY_VERIFIER_UNAVAILABLE}`);
        throw new AuthChainError(503, REASON_API_KEY_VERIFIER_UNAVAILABLE);
      }
      throw err;
    }
    if (outcome.outcome === 'rateLimited') {
      LOGGER.warn(`identity_auth_failed provider=${provider} reason_code=${REASON_API_KEY_RATE_LIMITED}`);
      throw new AuthChainRateLimitedError(REASON_API_KEY_RATE_LIMITED, outcome.retryAfterSeconds);
    }
    if (outcome.outcome !== 'ok') {
      LOGGER.warn(`identity_auth_failed provider=${provider} reason_code=${REASON_API_KEY_INVALID}`);
      throw new AuthChainError(401, REASON_API_KEY_INVALID);
    }
    LOGGER.log(`api_key_auth_ok provider=${provider} key_id=${outcome.keyId}`);
    const claims =
      outcome.expiresAt === null ? {} : { exp: Math.floor(Date.parse(outcome.expiresAt) / MILLISECONDS_PER_SECOND) };
    return {
      sub: outcome.keyId,
      userId: outcome.ownerId,
      provider,
      roles: mapApiKeyScopes(provider, outcome.scopes),
      principalType: API_KEYS.principalType,
      tenantId: outcome.tenantId,
      localIdentityMode: API_KEY_LOCAL_IDENTITY_MODE,
      // An API key carries no plan claim: the rate limiter applies the default plan.
      plan: '',
      claims,
      token: null,
      subject: outcome.keyId,
      profile: null,
      identity: claims,
    };
  }

  function routeApiKeyProviders(routeProviders: ReadonlyArray<string>): string[] {
    return routeProviders.filter((provider) => API_KEY_PROVIDERS.has(provider));
  }

  function presentsRouteApiKey(headers: RequestHeaders, routeProviders: ReadonlyArray<string>): boolean {
    return hasAdmittedApiKeyHeader(headers, routeApiKeyProviders(routeProviders));
  }

  /**
   * A presented key's outcome is final: a refused key throws (401, 429 with
   * `Retry-After`, or 503) and the bearer chain never runs to report a missing
   * token. A key header of a provider the route does not admit is never read.
   */
  async function authenticateRouteApiKey(
    headers: RequestHeaders,
    routeProviders: ReadonlyArray<string>,
  ): Promise<Principal | undefined> {
    const admitted = routeApiKeyProviders(routeProviders);
    if (!hasAdmittedApiKeyHeader(headers, admitted)) {
      return undefined;
    }
    return resolveApiKeyPrincipal(headers, admitted);
  }

  function requireProviders(principal: Principal, allowed: ReadonlyArray<string>): void {
    if (!allowed.includes(principal.provider)) {
      LOGGER.warn(`identity_provider_denied reason_code=${REASONS.providerNotAllowed}`);
      throw new AuthChainError(403, REASONS.providerNotAllowed);
    }
  }

  function requireRoles(principal: Principal, required: ReadonlyArray<string>): void {
    if (!required.some((role) => principal.roles.includes(role))) {
      LOGGER.warn(`identity_role_denied reason_code=${REASONS.roleDenied}`);
      throw new AuthChainError(403, REASONS.roleDenied);
    }
  }

  /** The principal's type is its provider's plan `principalType`. */
  function requirePrincipalTypes(principal: Principal, allowed: ReadonlyArray<string>): void {
    if (!allowed.includes(principal.principalType)) {
      LOGGER.warn(`identity_principal_type_denied reason_code=${REASONS.principalTypeMismatch}`);
      throw new AuthChainError(403, REASONS.principalTypeMismatch);
    }
  }

  return {
    authChainProblemBody,
    authenticateBearer,
    authenticateOptionalBearer,
    authenticateToken,
    bearerTokenOrForbidden,
    authenticateRouteRequest,
    authenticateOptionalRouteRequest,
    hasAdmittedApiKeyHeader,
    resolveApiKeyPrincipal,
    routeApiKeyProviders,
    presentsRouteApiKey,
    authenticateRouteApiKey,
    requireProviders,
    requireRoles,
    requirePrincipalTypes,
  };
}
