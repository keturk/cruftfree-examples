/**
 * Identity provider plan loader and JWKS validation core.
 *
 * Provides:
 * - Plan loading from a file, never from the environment: the plan bundled into
 *   the service's build output (the binding resolves its path beside its own
 *   compiled module, so the process working directory does not matter), else the
 *   deployment-static path baked at generation time (the platform's read-only
 *   mount). A missing, unreadable or unsupported plan throws;
 *   `loadIdentityPlanAtStartup` lets the process host fail at startup instead of
 *   answering requests with no plan.
 * - Per-provider remote JWKS key sets via `jose` `createRemoteJWKSet`, fetched from the
 *   plan's in-network `jwksFetch` endpoint when the entry carries one, else from `jwksUri`,
 *   and kept fresh for the entry's `jwksCacheTtlSeconds`.
 * - Token verification through `jwtVerify` with issuer + audience + plan-driven algorithm list.
 * - Role extraction through the plan `roleSource.claimPath` and `roleMappings`.
 *
 * Application settings read by this module (through the `lateBoundSetting` reader its
 * binding passes, never the environment directly):
 * - Every name listed in the `allowedAudienceRefs` of a provider — late-bound audience values
 *   that the identity provider assigns at provisioning time and so cannot be baked into the
 *   static plan: the Entra v2 access-token case, whose `aud` is the client-ID GUID that Graph
 *   assigns to the app registration.
 *   The platform delivers each value as an application setting under the name the plan declares.
 *
 * JWKS refresh failure fails closed (throws the JWKS-refresh-failed reason code).
 * A declared `allowedAudienceRefs` name whose setting is unset or empty fails closed
 * (throws) — it is never silently dropped, which would read as 'no audience constraint'.
 * Symmetric algorithms (HS*) and `alg:none` are rejected regardless of plan contents.
 *
 * Every project-specific value (reason codes, plan location, plan schema version, the
 * settings reader, the logger) is a parameter of `createIdentityCore`; the service's
 * `auth/identity.ts` binding passes them.
 *
 * Shipped by cruftfree-codegen-typescript-core and emitted verbatim. Do not edit manually.
 */
import { createRemoteJWKSet, decodeJwt, errors as joseErrors, importPKCS8, jwtVerify, SignJWT } from 'jose';
import type { JWTVerifyGetKey, JWTVerifyResult, JWTPayload, RemoteJWKSetOptions } from 'jose';
import { createHash, randomUUID } from 'node:crypto';
import * as fs from 'node:fs';
import * as http from 'node:http';
import * as https from 'node:https';
import { v5 as uuidv5 } from 'uuid';
import { classifyVerificationFailure } from './verification-failure';
import type { VerificationFailureReasonCodes } from './verification-failure';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/** Algorithm prefixes that are always rejected, regardless of plan contents. */
const REJECTED_ALG_PREFIXES: ReadonlyArray<string> = ['HS'];
/** The `none` algorithm — always rejected. */
const REJECTED_ALG_NONE = 'none';
/** The only URL schemes a signing-key endpoint may use; `https:` keeps certificate verification on. */
const KEY_FETCH_PROTOCOLS: ReadonlyArray<string> = ['http:', 'https:'];
/** A bare `host[:port]` Host header: a DNS name, an IPv4 address or a bracketed IPv6 address. */
const BARE_HOST_HEADER_PATTERN =
  /^(?<host>[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)*|\[[0-9A-Fa-f:.]+\])(?::(?<port>[1-9][0-9]{0,4}))?$/;
/** The longest host name a Host header may carry. */
const MAX_HOST_LENGTH = 253;
/** The highest port number a Host header may name. */
const MAX_PORT = 65535;
const MILLISECONDS_PER_SECOND = 1000;
/** Where a provider's second-factor proof is read: the verified token's own claims. */
const PROOF_SOURCE_TOKEN = 'token';
/** Where a provider's second-factor proof is read: the provider's answer about the token. */
const PROOF_SOURCE_INTROSPECTION = 'introspection';
/** The members an `introspection` object of a proof may carry. */
const INTROSPECTION_MEMBERS: ReadonlyArray<string> = ['url', 'hostHeader', 'credentialFile', 'cacheSeconds'];
/** The longest a proving answer may be remembered, in seconds. */
const INTROSPECTION_CACHE_SECONDS_MAX = 60;
/** How long one introspection request may take before the answer counts as unobtainable. */
const INTROSPECTION_TIMEOUT_MS = 5000;
/** The most proving answers remembered at once; the oldest is dropped first. */
const INTROSPECTION_CACHE_MAX_ENTRIES = 10000;
/** RFC 7523 client authentication by a signed assertion. */
const CLIENT_ASSERTION_TYPE = 'urn:ietf:params:oauth:client-assertion-type:jwt-bearer';
/** The signing algorithm of the client assertion. */
const CLIENT_ASSERTION_ALGORITHM = 'RS256';
/** How long a signed client assertion stays valid, in seconds: one question, not a session. */
const CLIENT_ASSERTION_LIFETIME_SECONDS = 60;
const HTTP_OK = 200;
/** The most bytes of an introspection answer read; a longer one is not an answer to this question. */
const MAX_ANSWER_BYTES = 1024 * 1024;

// ---------------------------------------------------------------------------
// Parameters
// ---------------------------------------------------------------------------

/**
 * The shared-vocabulary reason codes a failed verification is reported with: the
 * codes `classifyVerificationFailure` maps a `jose` failure to, and the provider
 * mismatch selection refuses with. The binding renders each from the vocabulary;
 * this module never spells one.
 */
export interface IdentityReasonCodes extends VerificationFailureReasonCodes {
  readonly providerMismatch: string;
  /** A `mfa = "required"` provider's verified token proves no second factor. */
  readonly mfaRequired: string;
}

/** Where this module's log lines go (the service's framework logger). */
export interface IdentityRuntimeLogger {
  log(message: string): void;
  warn(message: string): void;
  debug(message: string): void;
}

/** Everything project-specific the identity core needs, passed by the service's binding. */
export interface IdentityCoreOptions {
  readonly reasons: IdentityReasonCodes;
  /** The plan schema version the service was generated for; any other version fails the load. */
  readonly planSchemaVersion: number;
  /** The provider plan bundled into the service's build output. */
  readonly bundledPlanPath: string;
  /** The deployment-static plan path baked at generation time; null when the platform bakes none. */
  readonly bakedPlanPath: string | null;
  /** The application setting named `name`, or null when it is unset or empty. */
  readonly lateBoundSetting: (name: string) => string | null;
  readonly logger: IdentityRuntimeLogger;
}

// ---------------------------------------------------------------------------
// Verification failures
// ---------------------------------------------------------------------------

/**
 * A token that failed verification. `reasonCode` is the shared-vocabulary code
 * (logged server-side, never returned to a caller); the message IS the code, so
 * no exception text travels with it.
 *
 * Everything else this module throws -- a missing or unreadable plan, an
 * unsupported schema version, an invalid `localIdentity` mode, an unresolved
 * `allowedAudienceRefs` entry -- is a deployment or configuration defect, not a
 * property of the token, and stays a plain `Error`: the auth chain maps it to the
 * provider-config-error code.
 */
export class IdentityVerificationError extends Error {
  constructor(readonly reasonCode: string) {
    super(reasonCode);
    this.name = 'IdentityVerificationError';
  }
}

// ---------------------------------------------------------------------------
// Plan types (mirroring IdentityProviderPlan JSON shape)
// ---------------------------------------------------------------------------

interface RoleSourcePlan {
  readonly claimPath: string;
}

/** `namespace` is present only under the deterministicUuid5 mode. */
interface LocalIdentityPlan {
  readonly mode: string;
  readonly namespace?: string;
}

/** One identity attribute claim mapped to a plan field. */
interface AttributeMapping {
  readonly claimPath: string;
  readonly guarantee: string;
  readonly cruftfreeType: string;
  readonly nullable: boolean;
}

/** One projected profile field; `entity` and `key` are present only for an app-owned field. */
export interface ProfileFieldPlan {
  readonly source: string;
  readonly owner: string;
  readonly syncPolicy: string;
  readonly entity?: string;
  readonly key?: string;
}

/** The provider claims projected onto the application's profile store. */
export interface ProfileProjectionPlan {
  readonly enabled: boolean;
  readonly profileStore: string;
  readonly linkKey: ReadonlyArray<string>;
  readonly fields: Record<string, ProfileFieldPlan>;
}

/**
 * Where the signing keys are fetched from when `jwksUri` -- the provider's
 * public origin -- is not reachable from inside the deployment's network:
 * the in-network `url`, and the `hostHeader` the identity server routes its
 * instance by, when it needs one. It never changes the accepted issuer.
 */
interface JwksFetchPlan {
  readonly url: string;
  readonly hostHeader?: string;
}

/**
 * Where a provider is asked whether the session behind a token completed a second factor:
 * the in-network `url` of its RFC 7662 introspection endpoint, the `hostHeader` its identity
 * server routes by when it needs one, the `credentialFile` holding the signing key that
 * authenticates the question, and how many seconds (0 to 60) a proving answer is remembered.
 */
interface FactorIntrospectionPlan {
  readonly url: string;
  readonly hostHeader?: string;
  readonly credentialFile: string;
  readonly cacheSeconds: number;
}

/**
 * The second-factor proof every token of a `mfa = "required"` provider must carry: the
 * claim listing the authentication methods the sign-in completed (an RFC 8176 `amr`
 * array of strings) and the values any one of which proves a second factor. `source` says
 * where the claim is read: `token` (the verified access token) or `introspection` (the
 * provider's answer about the token, for a provider whose access tokens carry no
 * authentication methods); only an `introspection` source carries `introspection`.
 */
interface MfaFactorProofPlan {
  readonly claim: string;
  readonly provingValues: ReadonlyArray<string>;
  readonly source: typeof PROOF_SOURCE_TOKEN | typeof PROOF_SOURCE_INTROSPECTION;
  readonly introspection?: FactorIntrospectionPlan;
}

/** The shared container and cache block holding the denylist (logical names, never a connection string). */
export interface RevocationStorePlan {
  readonly shared: string;
  readonly block: string;
}

/** The RFC 7662 introspection endpoint of a provider; `secretHandle` is a logical handle, never a value. */
export interface IntrospectionPlan {
  readonly uri: string;
  readonly clientId: string;
  readonly secretHandle: string;
  readonly cacheSeconds: number;
}

/** The provider's revocation policy. `windowSeconds` and `store` are present only under denylist; `introspection` only under introspection. */
export interface RevocationPlan {
  readonly mode: string;
  readonly tokenIdClaim: string;
  readonly windowSeconds?: number;
  readonly store?: RevocationStorePlan;
  readonly introspection?: IntrospectionPlan;
}

/** Discriminator value of a JWT-validated provider entry. */
const CREDENTIAL_JWT = 'jwt';
/** Discriminator value of an API-key provider entry. */
const CREDENTIAL_API_KEY = 'apiKey';
/** Every credential kind this runtime understands; any other value fails the plan load. */
const KNOWN_CREDENTIALS: ReadonlyArray<string> = [CREDENTIAL_JWT, CREDENTIAL_API_KEY];

/**
 * A JWT-validated provider in the identity provider plan: the token's issuer
 * selects it, and its JWKS, algorithm and audience fields verify the token.
 */
interface JwtProviderPlanEntry {
  readonly credential: typeof CREDENTIAL_JWT;
  readonly name: string;
  readonly providerType: string;
  readonly audience: string;
  readonly mode: string;
  readonly principalType: string;
  readonly issuer: string;
  readonly jwksUri: string;
  readonly discoveryUri?: string;
  /** The in-network signing-key endpoint; when absent the keys are fetched from `jwksUri`. */
  readonly jwksFetch?: JwksFetchPlan;
  readonly allowedAlgorithms: ReadonlyArray<string>;
  readonly allowedAudiences: ReadonlyArray<string>;
  /**
   * Application-setting NAMES (never values) whose contents are unioned into the
   * effective audience allow-list at runtime. See `resolveEffectiveAudiences`.
   */
  readonly allowedAudienceRefs: ReadonlyArray<string>;
  /** Seconds a fetched key set stays fresh before the next verification refetches it. */
  readonly jwksCacheTtlSeconds: number;
  readonly revocation: RevocationPlan;
  /** Present only for a provider declaring `mfa = "required"`; see `provesSecondFactor`. */
  readonly mfaFactorProof?: MfaFactorProofPlan;
  readonly roleSource?: RoleSourcePlan;
  readonly roleMappings: Record<string, string>;
  readonly attributeMappings: Record<string, AttributeMapping>;
  readonly localIdentity: LocalIdentityPlan;
  readonly profileProjection?: ProfileProjectionPlan;
  readonly publicClientMetadataRef?: string;
  /** Secret-reference NAMES, never values. */
  readonly secretRefs: Record<string, string>;
}

/**
 * An API-key provider in the identity provider plan. Carries no issuer, JWKS or
 * algorithm fields: an API key is never a signed token, so this runtime never
 * validates it cryptographically and never selects this entry for a bearer
 * token -- the key is verified by the service that owns the key store.
 */
interface ApiKeyProviderPlanEntry {
  readonly credential: typeof CREDENTIAL_API_KEY;
  readonly name: string;
  readonly providerType: typeof CREDENTIAL_API_KEY;
  readonly audience: string;
  readonly mode: string;
  readonly principalType: string;
  /** Request header the key is read from. */
  readonly header: string;
  /** Service that owns the key store and answers verification requests. */
  readonly store: string;
  /** Path of the owning service's key-verification route. */
  readonly verifyPath: string;
  readonly roleMappings: Record<string, string>;
  /** Whether a verified key carries the tenant of its row. */
  readonly tenantMapped: boolean;
  /** Whether a verified key counts against the key's rate limit. */
  readonly consumesRateLimit: boolean;
}

/** Every provider-plan entry shape, discriminated by `credential`. */
type ProviderPlanEntry = JwtProviderPlanEntry | ApiKeyProviderPlanEntry;

function isJwtProviderPlanEntry(entry: ProviderPlanEntry): entry is JwtProviderPlanEntry {
  return entry.credential === CREDENTIAL_JWT;
}

interface IdentityProviderPlan {
  readonly schemaVersion: number;
  readonly application: string;
  readonly environment: string;
  readonly providers: Record<string, ProviderPlanEntry>;
}

// ---------------------------------------------------------------------------
// Principal context
// ---------------------------------------------------------------------------

/**
 * What every projected local profile document carries; the binding's
 * `IdentityProfileView` adds the service's own profile columns.
 */
export interface IdentityProfileDocument {
  readonly profileId: string;
}

/** Validated principal extracted from a provider-issued token, typed by its profile document. */
export interface IdentityPrincipalOf<TProfile extends IdentityProfileDocument> {
  /** Provider subject (hashed for audit; raw value retained in runtime context only). */
  readonly sub: string;
  /**
   * Stable local user id derived from (provider, sub) via the plan localIdentity strategy.
   * For deterministicUuid5: uuidv5(namespace, `${provider}:${sub}`) — read from plan, never hardcoded.
   * For subjectText: raw sub verbatim.
   * For projected: resolved via the profile service (IdentityProfile.profileId).
   */
  readonly userId: string;
  /** Logical provider name from the plan. */
  readonly provider: string;
  /** Normalized CruftFree roles held by the principal. */
  readonly roles: ReadonlyArray<string>;
  /** Principal type ('human' | 'machine'). */
  readonly principalType: string;
  /**
   * The principal's tenant. Set from an API-key row's mapped tenant field for an
   * API-key-authenticated principal, and from the profile-store row for a
   * JWT-authenticated principal whose provider's tenant claim is an app-owned
   * write-back field of this service's own store; `null` for every other
   * JWT-authenticated principal (its claim names the tenant) and for an API-key
   * principal whose provider maps no tenant field.
   */
  readonly tenantId: string | null;
  /**
   * The provider's plan `localIdentity.mode` ('deterministicUuid5' | 'subjectText' | 'projected').
   * A 'projected' principal carries an empty `userId` until the auth chain resolves its profile.
   */
  readonly localIdentityMode: string;
  /**
   * The verified subscription plan id: the first non-blank of the `plan`, `planId`
   * and `plan_id` claims of the VERIFIED payload, trimmed; '' when the credential
   * carries none (an API-key principal never does). The rate limiter reads this,
   * never a claim it decoded itself.
   */
  readonly plan: string;
  /** Raw JWT payload (for claim extraction by downstream handlers). */
  readonly claims: JWTPayload;
  /**
   * The validated bearer token the principal was authenticated with, forwardable
   * downstream. `null` when the principal holds no forwardable credential: an
   * API-key principal never carries one, because forwarding the raw key is
   * forbidden (read it only through `bearerTokenOrForbidden` in auth-chain.ts).
   */
  readonly token: string | null;
  /** The raw provider subject (what `Auth.subject` reads) -- distinct from the local `userId`. */
  readonly subject: string;
  /**
   * The projected local profile when the provider resolves its profile through the
   * auth chain, else `null` (what `Auth.profile` reads).
   */
  readonly profile: TProfile | null;
  /**
   * What `Auth.identity.<field>` reads: the verified claims, with each field the
   * provider declares read through its claim path. Whatever reads the token itself
   * (revocation, the tenant claim) reads `claims`, which a declared field never shadows.
   */
  readonly identity: JWTPayload;
}

// ---------------------------------------------------------------------------
// Plan validation
// ---------------------------------------------------------------------------

/**
 * Reject a plan carrying a provider entry whose `credential` is absent or not a
 * kind this runtime understands. Such an entry is never silently skipped: an
 * unknown credential kind means the plan was produced for a newer runtime.
 */
function assertKnownCredentials(plan: IdentityProviderPlan): void {
  // Typed as unknown: the value comes from untrusted JSON, not the declared shape.
  const providers: unknown = plan.providers;
  if (providers === null || typeof providers !== 'object' || Array.isArray(providers)) {
    throw new Error(
      `Identity provider plan has no 'providers' object (found ${Array.isArray(providers) ? 'array' : String(providers)}). ` +
        'Regenerate the service and its plan together.',
    );
  }
  for (const [key, entry] of Object.entries(plan.providers)) {
    // Typed as unknown: the value comes from untrusted JSON, not the declared union.
    const rawEntry: unknown = entry;
    const credential: unknown =
      rawEntry !== null && typeof rawEntry === 'object' ? (rawEntry as { credential?: unknown }).credential : undefined;
    if (typeof credential !== 'string' || !KNOWN_CREDENTIALS.includes(credential)) {
      throw new Error(
        `Identity provider plan entry '${key}' has credential kind '${String(credential)}', ` +
          `which this runtime does not support. Expected one of: ${KNOWN_CREDENTIALS.join(', ')}. ` +
          `Regenerate the plan and the service together so both use the same schema.`,
      );
    }
  }
}

/**
 * Reject a JWT provider entry whose signing-key fetch settings this runtime
 * cannot use safely: a `jwksCacheTtlSeconds` that is not a non-negative
 * integer, or a `jwksFetch` whose `url` is not an http(s) URL naming a host
 * without user information or a fragment, or whose `hostHeader` is not a bare
 * `host[:port]`. The values come from untrusted JSON, so they are checked when
 * the plan loads rather than on the first token. No error echoes the value.
 */
function assertKeyFetchSettings(plan: IdentityProviderPlan): void {
  for (const [key, entry] of Object.entries(plan.providers)) {
    if (!isJwtProviderPlanEntry(entry)) {
      continue;
    }
    const ttl: unknown = entry.jwksCacheTtlSeconds;
    if (typeof ttl !== 'number' || !Number.isInteger(ttl) || ttl < 0) {
      throw new Error(
        `Identity provider plan entry '${key}' has a jwksCacheTtlSeconds that is not a non-negative integer. ` +
          'Regenerate the plan and the service together.',
      );
    }
    // Typed as unknown: the value comes from untrusted JSON, not the declared shape.
    const fetchPlan: unknown = entry.jwksFetch;
    if (fetchPlan === undefined) {
      continue;
    }
    if (fetchPlan === null || typeof fetchPlan !== 'object' || Array.isArray(fetchPlan)) {
      throw new Error(
        `Identity provider plan entry '${key}' has a 'jwksFetch' member that is not an object. ` +
          'Expected { url, hostHeader? }. Regenerate the plan and the service together.',
      );
    }
    assertFetchEndpoint(key, 'jwksFetch', fetchPlan as { url?: unknown; hostHeader?: unknown });
  }
}

/**
 * Reject an endpoint object of a plan entry whose `url` is not an http(s) URL naming a
 * host without user information or a fragment, or whose `hostHeader` is not a bare
 * `host[:port]`. `member` names the object in the error; no error echoes a value.
 */
function assertFetchEndpoint(
  key: string,
  member: string,
  endpoint: { url?: unknown; hostHeader?: unknown },
): void {
  assertFetchUrl(key, `${member}.url`, endpoint.url);
  if (endpoint.hostHeader !== undefined && !isBareHostHeader(endpoint.hostHeader)) {
    throw new Error(
      `Identity provider plan entry '${key}' has a ${member}.hostHeader that is not a bare host[:port]. ` +
        'Regenerate the plan and the service together.',
    );
  }
}

/**
 * Reject a JWT provider entry whose `mfaFactorProof` this runtime cannot read exactly: a
 * `source` other than `token` or `introspection`, a `token` source that carries an
 * `introspection` object (nothing would read it), or an `introspection` source whose
 * object is missing, names an unusable endpoint or key file, carries a member this runtime
 * does not know, or asks for a `cacheSeconds` outside 0 to 60. The values come from untrusted
 * JSON, so they are checked when the plan loads: a proof read wrongly would admit tokens of a
 * provider that requires a second factor.
 */
function assertFactorProofs(plan: IdentityProviderPlan): void {
  for (const [key, entry] of Object.entries(plan.providers)) {
    if (!isJwtProviderPlanEntry(entry) || entry.mfaFactorProof === undefined) {
      continue;
    }
    const proof: unknown = entry.mfaFactorProof;
    if (proof === null || typeof proof !== 'object' || Array.isArray(proof)) {
      throw new Error(
        `Identity provider plan entry '${key}' has an 'mfaFactorProof' member that is not an object. ` +
          'Regenerate the plan and the service together.',
      );
    }
    const source: unknown = (proof as { source?: unknown }).source;
    const endpoint: unknown = (proof as { introspection?: unknown }).introspection;
    if (source === PROOF_SOURCE_TOKEN) {
      if (endpoint !== undefined) {
        throw new Error(
          `Identity provider plan entry '${key}' has an mfaFactorProof with a 'token' source that carries an ` +
            "'introspection' object. Regenerate the plan and the service together.",
        );
      }
      continue;
    }
    if (source !== PROOF_SOURCE_INTROSPECTION) {
      throw new Error(
        `Identity provider plan entry '${key}' has an mfaFactorProof whose 'source' is not one of ` +
          `'${PROOF_SOURCE_TOKEN}', '${PROOF_SOURCE_INTROSPECTION}'. Regenerate the plan and the service together.`,
      );
    }
    assertFactorIntrospection(key, endpoint);
  }
}

function assertFactorIntrospection(key: string, endpoint: unknown): void {
  if (endpoint === null || typeof endpoint !== 'object' || Array.isArray(endpoint)) {
    throw new Error(
      `Identity provider plan entry '${key}' has an mfaFactorProof with an 'introspection' source and no ` +
        "'introspection' object. Regenerate the plan and the service together.",
    );
  }
  const members = endpoint as { url?: unknown; hostHeader?: unknown; credentialFile?: unknown; cacheSeconds?: unknown };
  const undeclared = Object.keys(endpoint).filter((member) => !INTROSPECTION_MEMBERS.includes(member));
  if (undeclared.length > 0) {
    throw new Error(
      `Identity provider plan entry '${key}' has an mfaFactorProof.introspection with undeclared member(s) ` +
        `${undeclared.sort().join(', ')}. Regenerate the plan and the service together.`,
    );
  }
  assertFetchEndpoint(key, 'mfaFactorProof.introspection', members);
  if (typeof members.credentialFile !== 'string' || members.credentialFile === '') {
    throw new Error(
      `Identity provider plan entry '${key}' has an mfaFactorProof.introspection.credentialFile that is not a ` +
        'non-empty string. Regenerate the plan and the service together.',
    );
  }
  const cacheSeconds: unknown = members.cacheSeconds;
  if (
    typeof cacheSeconds !== 'number' ||
    !Number.isInteger(cacheSeconds) ||
    cacheSeconds < 0 ||
    cacheSeconds > INTROSPECTION_CACHE_SECONDS_MAX
  ) {
    throw new Error(
      `Identity provider plan entry '${key}' has an mfaFactorProof.introspection.cacheSeconds that is not an ` +
        `integer from 0 to ${INTROSPECTION_CACHE_SECONDS_MAX}. Regenerate the plan and the service together.`,
    );
  }
}

function assertFetchUrl(key: string, member: string, url: unknown): void {
  let parsed: URL | null = null;
  if (typeof url === 'string' && url.trim() === url && !/[\s\u0000-\u001f\u007f]/.test(url)) {
    try {
      parsed = new URL(url);
    } catch {
      parsed = null;
    }
  }
  if (
    parsed === null ||
    !KEY_FETCH_PROTOCOLS.includes(parsed.protocol) ||
    parsed.hostname === '' ||
    parsed.username !== '' ||
    parsed.password !== '' ||
    parsed.hash !== ''
  ) {
    throw new Error(
      `Identity provider plan entry '${key}' has a ${member} that is not an http or https URL naming a host ` +
        'without user information or a fragment. Regenerate the plan and the service together.',
    );
  }
}

function isBareHostHeader(value: unknown): boolean {
  if (typeof value !== 'string') {
    return false;
  }
  const match = BARE_HOST_HEADER_PATTERN.exec(value);
  if (match === null || match.groups === undefined || match.groups.host.length > MAX_HOST_LENGTH) {
    return false;
  }
  const port = match.groups.port;
  return port === undefined || Number(port) <= MAX_PORT;
}

// ---------------------------------------------------------------------------
// JWKS key set failures
// ---------------------------------------------------------------------------

/** A failure to fetch or read a provider's key set -- never a property of the token. */
class JwksFetchFailure extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'JwksFetchFailure';
  }
}

// ---------------------------------------------------------------------------
// Local user-id resolver
// ---------------------------------------------------------------------------

/**
 * Resolve the stable local user id for (providerName, subject) from the plan.
 *
 * Reads `localIdentity` from the already-loaded provider plan entry — never
 * a hardcoded namespace literal in this module.
 *
 * - deterministicUuid5: uuidv5(namespace, `${providerName}:${subject}`)
 *   Stateless, UUID-shaped, cross-service-identical for the same (provider, sub).
 * - subjectText: raw subject verbatim.
 * - projected: resolved via the profile service (IdentityProfile.profileId);
 *   this function throws if called for a projected provider — the profile path
 *   sets userId after profile resolution.
 *
 * @param providerEntry - The provider plan entry carrying the localIdentity block.
 * @param subject - Raw provider subject (`sub` claim).
 * @returns Stable local user id string.
 */
function resolveLocalUserId(providerEntry: JwtProviderPlanEntry, subject: string): string {
  const localIdentity = providerEntry.localIdentity;
  const mode = localIdentity.mode;
  if (mode === 'deterministicUuid5') {
    const namespace = localIdentity.namespace;
    if (!namespace) {
      throw new Error(
        `localIdentity mode='deterministicUuid5' for provider '${providerEntry.name}' ` +
          `is missing required 'namespace' field in the identity provider plan. ` +
          `Regenerate the provider plan to populate the namespace.`,
      );
    }
    return uuidv5(`${providerEntry.name}:${subject}`, namespace);
  }
  if (mode === 'subjectText') {
    return subject;
  }
  if (mode === 'projected') {
    // projected resolves via the profile service — the auth chain sets userId from
    // the profile store result; this function must not be called on the projected path.
    throw new Error(
      `resolveLocalUserId called for provider '${providerEntry.name}' in mode 'projected'. ` +
        `Projected mode resolves the local user id via the profile service (IdentityProfile.profileId), ` +
        `not the deterministic resolver. This is a generator bug — contact the CruftFree team.`,
    );
  }
  throw new Error(
    `Unknown localIdentity mode '${mode}' for provider '${providerEntry.name}'. ` +
      `Expected one of: 'deterministicUuid5', 'subjectText', 'projected'. ` +
      `Ensure the identity provider plan is up to date and regenerated with a compatible schema version.`,
  );
}

// ---------------------------------------------------------------------------
// Algorithm validation
// ---------------------------------------------------------------------------

function assertAlgorithmsAreAsymmetric(algorithms: ReadonlyArray<string>, providerName: string): void {
  for (const alg of algorithms) {
    if (alg.toLowerCase() === REJECTED_ALG_NONE) {
      throw new Error(
        `Provider '${providerName}' plan contains algorithm 'none' which is always rejected. ` +
          `Only asymmetric algorithms (RS*, ES*, PS*) are permitted.`,
      );
    }
    for (const prefix of REJECTED_ALG_PREFIXES) {
      if (alg.startsWith(prefix)) {
        throw new Error(
          `Provider '${providerName}' plan contains symmetric algorithm '${alg}' which is rejected. ` +
            `Only asymmetric algorithms (RS*, ES*, PS*) are permitted. ` +
            `Remove '${alg}' from allowedAlgorithms.`,
        );
      }
    }
  }
}

// ---------------------------------------------------------------------------
// Claim paths
// ---------------------------------------------------------------------------

/**
 * The value at a dot-separated claim path (e.g. "realm_access.roles"), or
 * `undefined` when a segment is missing or a non-object stands in its way.
 */
function resolveClaimPath(claims: Readonly<Record<string, unknown>>, claimPath: string): unknown {
  let cursor: unknown = claims as unknown;
  for (const part of claimPath.split('.')) {
    if (cursor === null || cursor === undefined || typeof cursor !== 'object') {
      return undefined;
    }
    cursor = (cursor as Record<string, unknown>)[part];
  }
  return cursor;
}

/** The status and text of an answer to a posted form. */
interface PostedForm {
  readonly status: number;
  readonly text: string;
}

/**
 * POST an urlencoded form and return the answer. The request goes through `node:http(s)`
 * because `fetch` replaces a `Host` header with the URL's own host, and an identity server
 * that routes its instance by `Host` would then answer for the wrong one. The wait is
 * bounded by `timeoutMs`, and so is the size of the answer read.
 *
 * @throws Error on a transport failure, a timeout, or an answer over `MAX_ANSWER_BYTES`.
 */
function postForm(
  url: string,
  headers: Readonly<Record<string, string>>,
  body: string,
  timeoutMs: number,
): Promise<PostedForm> {
  const target = new URL(url);
  const transport = target.protocol === 'https:' ? https : http;
  return new Promise<PostedForm>((resolve, reject) => {
    const request = transport.request(
      target,
      { method: 'POST', headers: { ...headers, 'Content-Length': Buffer.byteLength(body) }, timeout: timeoutMs },
      (response) => {
        const chunks: Buffer[] = [];
        let received = 0;
        response.on('data', (chunk: Buffer) => {
          received += chunk.length;
          if (received > MAX_ANSWER_BYTES) {
            request.destroy(new Error('the answer is too long'));
            return;
          }
          chunks.push(chunk);
        });
        response.on('end', () => {
          resolve({ status: response.statusCode ?? 0, text: Buffer.concat(chunks).toString('utf-8') });
        });
        response.on('error', reject);
      },
    );
    request.on('timeout', () => request.destroy(new Error('the request timed out')));
    request.on('error', reject);
    request.end(body);
  });
}

/**
 * @throws Error when the plan's `mfaFactorProof` names no readable claim or proving values
 *   (a deployment defect, never a property of the token).
 */
function assertFactorProofReadable(proof: MfaFactorProofPlan): void {
  const provingValues: unknown = proof.provingValues;
  if (
    typeof proof.claim !== 'string' ||
    !Array.isArray(provingValues) ||
    !provingValues.every((value) => typeof value === 'string')
  ) {
    throw new Error(
      'Identity provider plan: mfaFactorProof is malformed (claim must be a string and ' +
        'provingValues an array of strings). Regenerate the service and its plan together.',
    );
  }
}

/**
 * Whether `claims` -- the verified token's, or the provider's introspection answer about it
 * -- prove a second factor: the proof's claim is an array of strings holding at least one of
 * its proving values. Absent, not an array, or none of the values is `false` -- never a pass.
 *
 * @throws Error when the plan's `mfaFactorProof` is malformed (a deployment defect).
 */
function provesSecondFactor(claims: Readonly<Record<string, unknown>>, proof: MfaFactorProofPlan): boolean {
  assertFactorProofReadable(proof);
  const methods = resolveClaimPath(claims, proof.claim);
  return (
    Array.isArray(methods) &&
    methods.some((method) => typeof method === 'string' && proof.provingValues.includes(method))
  );
}

/**
 * The verified claims as `Auth.identity` reads them. A declared field is read
 * through its claim path, so `fullName` mapped to `name` holds the token's `name`.
 * A field the token does not carry is `null`, even when the token holds a claim
 * spelled like the field: only the provider's declaration says what the field
 * means. Every other claim keeps its own name.
 */
function declaredIdentity(claims: JWTPayload, provider: JwtProviderPlanEntry): JWTPayload {
  const identity: Record<string, unknown> = { ...claims };
  for (const [field, mapping] of Object.entries(provider.attributeMappings)) {
    identity[field] = resolveClaimPath(claims, mapping.claimPath) ?? null;
  }
  return identity;
}

// ---------------------------------------------------------------------------
// Role extraction
// ---------------------------------------------------------------------------

function extractRolesFromClaims(
  claims: JWTPayload,
  provider: JwtProviderPlanEntry,
): ReadonlyArray<string> {
  const roleSource = provider.roleSource;
  if (!roleSource) {
    return [];
  }
  const cursor = resolveClaimPath(claims, roleSource.claimPath);
  // Two claim shapes carry roles. A map -- the self-hosted identity provider's
  // default, `{roleKey: {orgId: orgDomain}}` -- names its roles by its KEYS (the
  // nested values are organization metadata); an external provider may deliver
  // a flat list of role-name strings. Any other value grants no role.
  const rawRoles: ReadonlyArray<string> = Array.isArray(cursor)
    ? (cursor as unknown[]).filter((r): r is string => typeof r === 'string')
    : cursor !== null && typeof cursor === 'object'
      ? Object.keys(cursor)
      : [];

  // Apply roleMappings: map provider-local role name → CruftFree role name.
  const mappings = provider.roleMappings;
  const normalized: string[] = [];
  for (const raw of rawRoles) {
    const mapped = mappings[raw];
    if (mapped !== undefined) {
      normalized.push(mapped);
    } else {
      normalized.push(raw);
    }
  }
  return normalized;
}

// ---------------------------------------------------------------------------
// Token claims
// ---------------------------------------------------------------------------

/** The token's `aud` claim normalized to a set (a JWT carries a string or an array). */
function tokenAudiences(payload: JWTPayload): ReadonlySet<string> {
  const aud = payload.aud;
  if (typeof aud === 'string') {
    return new Set([aud]);
  }
  return new Set(Array.isArray(aud) ? aud.filter((a): a is string => typeof a === 'string') : []);
}

/** Plan claim names, in precedence order. */
const PLAN_CLAIM_NAMES: ReadonlyArray<string> = ['plan', 'planId', 'plan_id'];

/** The plan id of a verified payload; '' when none of the plan claims is present and non-blank. */
function planFromClaims(claims: JWTPayload): string {
  for (const name of PLAN_CLAIM_NAMES) {
    const value = claims[name];
    if (value !== undefined && value !== null && String(value).trim() !== '') {
      return String(value).trim();
    }
  }
  return '';
}

// ---------------------------------------------------------------------------
// The identity core of one service
// ---------------------------------------------------------------------------

/** The identity operations a service's binding exports. */
export interface IdentityCore<TProfile extends IdentityProfileDocument> {
  /**
   * Load the identity provider plan when the process starts, so a missing,
   * unreadable or unsupported plan stops the host before it serves a request
   * rather than failing every authenticated request afterwards.
   *
   * @throws Error naming what was missing and where the plan was expected.
   */
  readonly loadIdentityPlanAtStartup: () => void;
  /**
   * The revocation policy of a JWT *provider* in the loaded plan, or `undefined` when the plan
   * has no such JWT provider (an unknown name, or an API-key provider, which carries none).
   * The revocation module treats `undefined` as "status unknown" and fails closed.
   *
   * @throws Error when the plan cannot be loaded (the same failure `verifyIdentityToken` raises).
   */
  readonly providerRevocationPolicy: (provider: string) => RevocationPlan | undefined;
  /**
   * The enabled profile projection of a JWT *provider* in the loaded plan, or `undefined` when the
   * provider is unknown, an API-key provider, or projects no profile.
   *
   * @throws Error when the plan cannot be loaded (the same failure `verifyIdentityToken` raises).
   */
  readonly providerProfileProjection: (provider: string) => ProfileProjectionPlan | undefined;
  /**
   * Verify a Bearer token (without the 'Bearer ' prefix) against the loaded identity provider plan.
   *
   * @throws IdentityVerificationError carrying the vocabulary code of the failure
   *   (provider mismatch, expired token, issuer or audience mismatch, bad
   *   signature, malformed token, JWKS refresh failure). Any other thrown error is
   *   a deployment or configuration defect, never a property of the token.
   */
  readonly verifyIdentityToken: (token: string) => Promise<IdentityPrincipalOf<TProfile>>;
}

/**
 * The identity core of one service: the plan it loads (once, cached), the key sets it
 * fetches (one per provider, cached) and the token verification over both.
 */
export function createIdentityCore<TProfile extends IdentityProfileDocument>(
  coreOptions: IdentityCoreOptions,
): IdentityCore<TProfile> {
  const LOGGER = coreOptions.logger;
  const PLAN_SCHEMA_VERSION_SUPPORTED = coreOptions.planSchemaVersion;
  const BUNDLED_PLAN_PATH = coreOptions.bundledPlanPath;
  const BAKED_PLAN_PATH = coreOptions.bakedPlanPath;
  const lateBoundSetting = coreOptions.lateBoundSetting;
  const REASONS = coreOptions.reasons;
  const REASON_MALFORMED_TOKEN = REASONS.malformedToken;
  const REASON_BAD_SIGNATURE = REASONS.badSignature;
  const REASON_JWKS_REFRESH_FAILED = REASONS.jwksRefreshFailed;
  const REASON_PROVIDER_MISMATCH = REASONS.providerMismatch;
  const REASON_MFA_REQUIRED = REASONS.mfaRequired;

  let _cachedPlan: IdentityProviderPlan | null = null;
  const _jwksSets = new Map<string, JWTVerifyGetKey>();
  /** `sha256(token)` -> expiry (epoch ms) of a proving answer, least recently used first. */
  const _provenFactors = new Map<string, number>();

  /**
   * Resolve the identity provider plan file. No environment variable is read.
   *
   * Resolution order (deployment-static, independent of the working directory):
   *   1. The plan bundled into the service's build output (`BUNDLED_PLAN_PATH`) --
   *      how a platform that ships the plan inside the service package delivers it.
   *   2. The baked `BAKED_PLAN_PATH` -- how a platform that mounts the plan at a
   *      fixed path delivers it.
   *
   * @throws Error when neither a bundled plan nor a baked path exists.
   */
  function resolvePlanPath(): string {
    if (fs.existsSync(BUNDLED_PLAN_PATH)) {
      return BUNDLED_PLAN_PATH;
    }
    if (BAKED_PLAN_PATH !== null) {
      return BAKED_PLAN_PATH;
    }
    throw new Error(
      `Identity provider plan not found: no plan is bundled at '${BUNDLED_PLAN_PATH}' ` +
        'and this platform bakes no plan path. The plan must ship inside the service ' +
        'build output or be mounted at the baked path. Regenerate the service.',
    );
  }

  function loadIdentityPlan(): IdentityProviderPlan {
    if (_cachedPlan !== null) {
      return _cachedPlan;
    }
    const planPath = resolvePlanPath();
    let raw: string;
    try {
      raw = fs.readFileSync(planPath, 'utf-8');
    } catch (err) {
      throw new Error(
        `Failed to read identity provider plan from '${planPath}': ` +
          `${err instanceof Error ? err.message : String(err)}. ` +
          `Expected the plan bundled at '${BUNDLED_PLAN_PATH}'` +
          (BAKED_PLAN_PATH !== null ? ` or mounted at '${BAKED_PLAN_PATH}'` : '') +
          '. Ensure the file exists and is readable by the process.',
      );
    }
    let plan: IdentityProviderPlan;
    try {
      plan = JSON.parse(raw) as IdentityProviderPlan;
    } catch (err) {
      throw new Error(
        `Failed to parse identity provider plan JSON from '${planPath}': ` +
          `${err instanceof Error ? err.message : String(err)}. ` +
          'Regenerate the service and its plan together.',
      );
    }
    if (plan.schemaVersion !== PLAN_SCHEMA_VERSION_SUPPORTED) {
      throw new Error(
        `Identity provider plan schema version ${plan.schemaVersion} is not supported. ` +
          `This runtime supports schema version ${PLAN_SCHEMA_VERSION_SUPPORTED}. ` +
          `Upgrade the runtime or regenerate the plan with a compatible schema version.`,
      );
    }
    assertKnownCredentials(plan);
    assertKeyFetchSettings(plan);
    assertFactorProofs(plan);
    _cachedPlan = plan;
    LOGGER.log(
      `identity_plan_loaded path=${planPath} application=${plan.application} environment=${plan.environment}`,
    );
    return _cachedPlan;
  }

  function loadIdentityPlanAtStartup(): void {
    loadIdentityPlan();
  }

  function providerRevocationPolicy(provider: string): RevocationPlan | undefined {
    const entry = loadIdentityPlan().providers[provider];
    return entry !== undefined && isJwtProviderPlanEntry(entry) ? entry.revocation : undefined;
  }

  function providerProfileProjection(provider: string): ProfileProjectionPlan | undefined {
    const entry = loadIdentityPlan().providers[provider];
    if (entry === undefined || !isJwtProviderPlanEntry(entry)) {
      return undefined;
    }
    const projection = entry.profileProjection;
    return projection !== undefined && projection.enabled ? projection : undefined;
  }

  /**
   * The key set of *provider*, fetched from the plan's in-network `jwksFetch.url`
   * (presenting `jwksFetch.hostHeader` as the Host header when the plan gives
   * one) and from `jwksUri` otherwise. Both come only from the loaded plan. An
   * https endpoint is fetched with certificate verification on; with a Host
   * header the certificate is checked against that host name.
   *
   * A key the set does not hold is reported as jose reports it; any other
   * failure to obtain the set (unreachable endpoint, non-200 answer, timeout,
   * a body that is not a key set) is a `JwksFetchFailure`.
   */
  function getJwksSetForProvider(provider: JwtProviderPlanEntry): JWTVerifyGetKey {
    const cached = _jwksSets.get(provider.name);
    if (cached !== undefined) {
      return cached;
    }
    const fetchPlan = provider.jwksFetch;
    const options: RemoteJWKSetOptions = {
      cacheMaxAge: provider.jwksCacheTtlSeconds * MILLISECONDS_PER_SECOND,
    };
    if (fetchPlan?.hostHeader !== undefined) {
      options.headers = { host: fetchPlan.hostHeader };
    }
    const remote = createRemoteJWKSet(new URL(fetchPlan !== undefined ? fetchPlan.url : provider.jwksUri), options);
    const keySet: JWTVerifyGetKey = async (protectedHeader, token) => {
      try {
        return await remote(protectedHeader, token);
      } catch (err) {
        if (err instanceof joseErrors.JWKSNoMatchingKey || err instanceof joseErrors.JWKSMultipleMatchingKeys) {
          throw err;
        }
        throw new JwksFetchFailure(err instanceof Error ? err.message : String(err));
      }
    };
    _jwksSets.set(provider.name, keySet);
    return keySet;
  }

  /**
   * Whether the session behind the verified `token` completed a second factor, per the
   * provider's `proof`: read from the token's own claims, or from the provider's answer about
   * the token when its access tokens carry no authentication methods.
   *
   * @throws Error when the proof is malformed (a deployment defect).
   */
  async function provesFactor(
    token: string,
    claims: JWTPayload,
    provider: JwtProviderPlanEntry,
    proof: MfaFactorProofPlan,
  ): Promise<boolean> {
    if (proof.source !== PROOF_SOURCE_INTROSPECTION || proof.introspection === undefined) {
      return provesSecondFactor(claims, proof);
    }
    assertFactorProofReadable(proof);
    const cacheKey = createHash('sha256').update(token).digest('hex');
    const remembered = _provenFactors.get(cacheKey);
    if (remembered !== undefined) {
      if (remembered > Date.now()) {
        _provenFactors.delete(cacheKey);
        _provenFactors.set(cacheKey, remembered);
        return true;
      }
      _provenFactors.delete(cacheKey);
    }
    let answer: Readonly<Record<string, unknown>>;
    try {
      answer = await askProviderAboutToken(token, provider, proof.introspection);
    } catch (err) {
      // An answer that cannot be obtained proves nothing; it is logged apart from a
      // refusal so an outage is not read as an attack. The caller refuses the token.
      LOGGER.warn(
        `identity_mfa_introspection_unavailable provider=${provider.name} ` +
          `problem=${err instanceof Error ? err.message : 'unknown'}`,
      );
      return false;
    }
    if (answer.active !== true || String(answer.sub) !== String(claims.sub ?? '')) {
      return false;
    }
    if (!provesSecondFactor(answer, proof)) {
      return false;
    }
    rememberProvenFactor(cacheKey, claims, proof.introspection.cacheSeconds);
    return true;
  }

  /** Remember a proving answer until its cache time or the token's own expiry, whichever is first. */
  function rememberProvenFactor(cacheKey: string, claims: JWTPayload, cacheSeconds: number): void {
    if (cacheSeconds <= 0) {
      return;
    }
    let expires = Date.now() + cacheSeconds * MILLISECONDS_PER_SECOND;
    if (typeof claims.exp === 'number') {
      expires = Math.min(expires, claims.exp * MILLISECONDS_PER_SECOND);
    }
    _provenFactors.set(cacheKey, expires);
    while (_provenFactors.size > INTROSPECTION_CACHE_MAX_ENTRIES) {
      const oldest = _provenFactors.keys().next();
      if (oldest.done === true) {
        break;
      }
      _provenFactors.delete(oldest.value);
    }
  }

  /**
   * The signed client assertion that authenticates the question (RFC 7523). The key file is
   * read each time, so a rotated key is used at once and no key stays in memory.
   *
   * @throws Error when the key file is unreadable or does not hold `keyId`, `key` and `clientId`.
   */
  async function signClientAssertion(credentialFile: string, issuer: string): Promise<string> {
    let document: unknown;
    try {
      document = JSON.parse(fs.readFileSync(credentialFile, 'utf-8'));
    } catch {
      throw new Error('the introspection key file is unreadable');
    }
    const { keyId, key, clientId } =
      document !== null && typeof document === 'object'
        ? (document as { keyId?: unknown; key?: unknown; clientId?: unknown })
        : { keyId: undefined, key: undefined, clientId: undefined };
    if (
      typeof keyId !== 'string' || keyId === '' ||
      typeof key !== 'string' || key === '' ||
      typeof clientId !== 'string' || clientId === ''
    ) {
      throw new Error('the introspection key file does not hold keyId, key and clientId');
    }
    const privateKey = await importPKCS8(key, CLIENT_ASSERTION_ALGORITHM);
    return new SignJWT({})
      .setProtectedHeader({ alg: CLIENT_ASSERTION_ALGORITHM, kid: keyId })
      .setIssuer(clientId)
      .setSubject(clientId)
      .setAudience(issuer)
      .setIssuedAt()
      .setExpirationTime(`${CLIENT_ASSERTION_LIFETIME_SECONDS}s`)
      .setJti(randomUUID())
      .sign(privateKey);
  }

  /**
   * POST the signed question to the provider's introspection endpoint and return its JSON answer.
   *
   * @throws Error naming the step that failed, never a token, a key or a response body.
   */
  async function askProviderAboutToken(
    token: string,
    provider: JwtProviderPlanEntry,
    endpoint: FactorIntrospectionPlan,
  ): Promise<Readonly<Record<string, unknown>>> {
    const form = new URLSearchParams({
      client_assertion_type: CLIENT_ASSERTION_TYPE,
      client_assertion: await signClientAssertion(endpoint.credentialFile, provider.issuer),
      token,
      token_type_hint: 'access_token',
    });
    const headers: Record<string, string> = {
      'Content-Type': 'application/x-www-form-urlencoded',
      Accept: 'application/json',
    };
    if (endpoint.hostHeader !== undefined) {
      headers.Host = endpoint.hostHeader;
    }
    let response: PostedForm;
    try {
      response = await postForm(endpoint.url, headers, form.toString(), INTROSPECTION_TIMEOUT_MS);
    } catch {
      throw new Error('the introspection request failed');
    }
    if (response.status !== HTTP_OK) {
      throw new Error(`the introspection answer is HTTP ${response.status}, not ${HTTP_OK}`);
    }
    let body: unknown;
    try {
      body = JSON.parse(response.text);
    } catch {
      throw new Error('the introspection answer is not JSON');
    }
    if (body === null || typeof body !== 'object' || Array.isArray(body)) {
      throw new Error('the introspection answer is not an object');
    }
    return body as Readonly<Record<string, unknown>>;
  }

  /**
   * Resolve the effective audience allow-list for a provider.
   *
   * The plan carries two sources and the effective list is their union:
   * - `allowedAudiences` — static values baked in at generation time.
   * - `allowedAudienceRefs` — application-setting NAMES whose values the identity
   *   provider assigns at provisioning time and which therefore cannot be baked
   *   into a static plan: the Entra v2 access-token case, whose `aud` is the
   *   client-ID GUID assigned to the app registration at deploy time.
   *
   * A declared ref whose setting is unset or empty throws. It is never
   * skipped: `verifyIdentityToken` reads an empty effective list as meaning the
   * provider does not constrain audience, and omits the `jwtVerify` audience option,
   * so a silently-dropped ref would widen the allow-list to every audience. Failing
   * closed here makes the unresolved case impossible to confuse with the
   * deliberately-unconstrained one.
   *
   * @param provider - The provider plan entry carrying both audience sources.
   * @returns The de-duplicated effective audience allow-list.
   */
  function resolveEffectiveAudiences(provider: JwtProviderPlanEntry): ReadonlyArray<string> {
    const effective = new Set<string>(provider.allowedAudiences);
    for (const envName of provider.allowedAudienceRefs) {
      const value = lateBoundSetting(envName);
      if (value === null) {
        throw new Error(
          `Provider '${provider.name}' declares allowedAudienceRefs entry '${envName}', ` +
            `but the application setting ${envName} is unset or empty. ` +
            `Expected the audience value assigned to the application registration ` +
            `at deployment time, delivered as an application setting named ${envName}. ` +
            `An unresolved reference is never treated as 'no audience constraint' — ` +
            `set ${envName} in the service configuration, or remove '${envName}' from ` +
            `allowedAudienceRefs in the identity provider plan.`,
        );
      }
      effective.add(value);
    }
    return [...effective];
  }

  /**
   * Select the provider plan entry that owns the token: issuer first, then audience.
   * Only JWT-credentialed entries are candidates -- an API-key entry has no issuer
   * and is never selected for a bearer token.
   *
   * One OIDC instance can host several providers that share an issuer and differ
   * only by audience, so matching on the issuer alone would let the first
   * declared provider claim every token from that instance. Rules, in order:
   *   1. Gather every provider whose `issuer` equals the token `iss`.
   *   2. Exactly one match: use it (audience is enforced by `jwtVerify`).
   *   3. Several share the issuer: prefer the one whose effective audiences
   *      intersect the token `aud`.
   *   4. Otherwise prefer a provider whose effective audience list is empty.
   *   5. Otherwise take the first issuer match, so verification fails closed
   *      with a deterministic audience mismatch.
   * An unresolvable `allowedAudienceRefs` entry throws (see
   * `resolveEffectiveAudiences`), so rule 4 is never reached by an unset ref.
   *
   * @param plan - The loaded identity provider plan.
   * @param payload - The token's UNVERIFIED payload (used only for selection).
   * @returns The selected provider plan entry.
   * @throws IdentityVerificationError (provider-mismatch code) when no provider's
   *   issuer matches the token.
   */
  function selectProvider(plan: IdentityProviderPlan, payload: JWTPayload): JwtProviderPlanEntry {
    const tokenIssuer = typeof payload.iss === 'string' ? payload.iss : '';
    const issuerMatches = Object.values(plan.providers)
      .filter(isJwtProviderPlanEntry)
      .filter((provider) => provider.issuer === tokenIssuer);
    if (issuerMatches.length === 0) {
      throw new IdentityVerificationError(REASON_PROVIDER_MISMATCH);
    }
    if (issuerMatches.length === 1) {
      return issuerMatches[0];
    }
    const audiences = tokenAudiences(payload);
    const resolved = issuerMatches.map((provider) => ({
      provider,
      allowed: resolveEffectiveAudiences(provider),
    }));
    const byAudience = resolved.find(({ allowed }) => allowed.some((aud) => audiences.has(aud)));
    if (byAudience !== undefined) {
      return byAudience.provider;
    }
    const unconstrained = resolved.find(({ allowed }) => allowed.length === 0);
    if (unconstrained !== undefined) {
      return unconstrained.provider;
    }
    return issuerMatches[0];
  }

  /**
   * Verify a Bearer token against the loaded identity provider plan.
   *
   * Selects the owning provider across every plan provider by issuer, then
   * audience (`selectProvider`), and verifies the token against that one
   * provider with `createRemoteJWKSet` + `jwtVerify`. Which providers a route
   * accepts is NOT decided here: the auth chain's `requireProviders` enforces a
   * route's provider allow-list against the verified `principal.provider`.
   *
   * @param token - Raw Bearer token (without 'Bearer ' prefix).
   * @returns Resolved principal on success.
   * @throws IdentityVerificationError carrying the vocabulary code of the failure
   *   (provider mismatch, expired token, issuer or audience mismatch, bad
   *   signature, malformed token, JWKS refresh failure). Any other thrown error is
   *   a deployment or configuration defect, never a property of the token.
   */
  async function verifyIdentityToken(token: string): Promise<IdentityPrincipalOf<TProfile>> {
    const plan = loadIdentityPlan();

    let unverifiedPayload: JWTPayload;
    try {
      unverifiedPayload = decodeJwt(token);
    } catch {
      throw new IdentityVerificationError(REASON_MALFORMED_TOKEN);
    }
    const providerEntry = selectProvider(plan, unverifiedPayload);
    const providerName = providerEntry.name;

    // Guard: reject symmetric algorithms before touching the key set.
    try {
      assertAlgorithmsAreAsymmetric(providerEntry.allowedAlgorithms, providerName);
    } catch {
      throw new IdentityVerificationError(REASON_BAD_SIGNATURE);
    }

    // Union the static allow-list with the setting-resolved late-bound audiences.
    // Throws (fail closed) when a declared ref cannot be resolved — never
    // classified as a token failure, since it is a deployment misconfiguration
    // and not a property of the token.
    const effectiveAudiences = resolveEffectiveAudiences(providerEntry);

    const jwks = getJwksSetForProvider(providerEntry);

    let result: JWTVerifyResult;
    try {
      result = await jwtVerify(token, jwks, {
        issuer: providerEntry.issuer,
        audience: effectiveAudiences.length > 0
          ? (effectiveAudiences as string[])
          : undefined,
        algorithms: providerEntry.allowedAlgorithms as string[],
      });
    } catch (err) {
      // A key-set fetch failure is typed by its class; every other failure is classified by the shared mapping.
      const reason = err instanceof JwksFetchFailure
        ? REASON_JWKS_REFRESH_FAILED
        : classifyVerificationFailure(err, REASONS);
      if (reason === REASON_JWKS_REFRESH_FAILED) {
        LOGGER.warn(`identity_jwks_refresh_failed provider=${providerName} reason_code=${reason}`);
      }
      throw new IdentityVerificationError(reason);
    }

    const claims = result.payload;
    // A `required` provider's token must prove its second factor: the service checks the
    // proof itself rather than trusting the provider's configuration. The proof is read
    // from the token, or from the provider's answer about it when its tokens carry none.
    const factorProof = providerEntry.mfaFactorProof;
    if (factorProof !== undefined && !(await provesFactor(token, claims, providerEntry, factorProof))) {
      LOGGER.warn(
        `identity_auth_failed reason_code=${REASON_MFA_REQUIRED} claim=${factorProof.claim} ` +
          `provider=${providerName}`,
      );
      throw new IdentityVerificationError(REASON_MFA_REQUIRED);
    }
    const roles = extractRolesFromClaims(claims, providerEntry);
    const sub = typeof claims.sub === 'string' ? claims.sub : '';

    // Resolve the stable local user id from the plan localIdentity strategy.
    // projected mode: userId is '' here — the auth chain resolves it from the
    // profile store and denies the request when it cannot.
    const localMode = providerEntry.localIdentity.mode;
    const userId = localMode === 'projected' ? '' : resolveLocalUserId(providerEntry, sub);

    LOGGER.debug(`identity_token_verified provider=${providerName}`);

    const identity = declaredIdentity(claims, providerEntry);

    return {
      sub,
      userId,
      provider: providerName,
      roles,
      principalType: providerEntry.principalType,
      tenantId: null,
      localIdentityMode: localMode,
      plan: planFromClaims(claims),
      claims,
      token,
      subject: sub,
      profile: null,
      identity,
    };
  }

  return {
    loadIdentityPlanAtStartup,
    providerRevocationPolicy,
    providerProfileProjection,
    verifyIdentityToken,
  };
}
