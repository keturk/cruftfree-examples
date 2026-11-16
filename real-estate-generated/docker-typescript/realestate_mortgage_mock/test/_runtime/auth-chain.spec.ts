/**
 * Jest spec of the auth chain runtime module (`src/_runtime/auth-chain.ts`).
 *
 * The chain runs over in-spec implementations of every contract its binding passes: a
 * token verifier that answers per token, a revocation list, a profile loader, an API-key
 * store keyed by key hash, a profile store holding rows in memory and a metadata writer
 * that records each write. Every branch of the chain is covered: no credential, an invalid
 * credential, each auth mode it resolves (bearer, projected profile, revocation, API key,
 * optional, identity write-back), the authorization checks, and the refusal shape
 * (status, opaque detail, `Retry-After`, problem body).
 *
 * Shipped by cruftfree-codegen-typescript-core and emitted verbatim. Do not edit manually.
 */
import { ForbiddenException } from '@nestjs/common';
import { createHash } from 'node:crypto';
import {
  AuthChainError,
  AuthChainRateLimitedError,
  AuthChainRevocationUnavailableError,
  REASON_API_KEY_AMBIGUOUS,
  authChainFailureDetail,
  authChainFailureHeaders,
  createAuthChain,
  writeBackText,
} from '../../src/_runtime/auth-chain';
import type {
  ApiKeyOutcome,
  AuthChain,
  AuthChainApiKeys,
  AuthChainLogger,
  AuthChainOptions,
  AuthChainReasonCodes,
  AuthChainRevocation,
  AuthChainStatus,
  AuthChainWriteBack,
  RequestHeaders,
  WriteBackCall,
  WriteBackStore,
} from '../../src/_runtime/auth-chain';
import { IdentityVerificationError } from '../../src/_runtime/identity';
import type { IdentityPrincipalOf, IdentityProfileDocument } from '../../src/_runtime/identity';

const REASONS: AuthChainReasonCodes = {
  missingToken: 'test_missing_token',
  providerNotAllowed: 'test_provider_not_allowed',
  roleDenied: 'test_role_denied',
  principalTypeMismatch: 'test_principal_type_mismatch',
  profileUnavailable: 'test_profile_unavailable',
  providerConfigError: 'test_provider_config_error',
  noForwardableToken: 'test_no_forwardable_token',
};

const PROVIDER = 'customer';
const OTHER_PROVIDER = 'partner';
const SUBJECT = 'subject-1';
const USER_ID = 'user-1';
const VALID_TOKEN = 'valid-token';
const PROJECTED_TOKEN = 'projected-token';
const PARTNER_TOKEN = 'partner-token';
const BAD_SIGNATURE_TOKEN = 'bad-signature-token';
const CONFIG_ERROR_TOKEN = 'config-error-token';
const REASON_BAD_SIGNATURE = 'test_bad_signature';
const REASON_TOKEN_REVOKED = 'test_token_revoked';
const REASON_REVOCATION_UNAVAILABLE = 'test_revocation_unavailable';
const REVOCATION_RETRY_AFTER_SECONDS = 30;
const RATE_LIMIT_RETRY_AFTER_SECONDS = 12;
const INSTANCE = '/orders/1';

const KEY_PROVIDER = 'storefront-keys';
const KEY_HEADER = 'x-api-key';
const OTHER_KEY_PROVIDER = 'partner-keys';
const OTHER_KEY_HEADER = 'x-partner-key';
const KEY_PRINCIPAL_TYPE = 'human';
const VALID_KEY = 'sk_live_valid_key_0001';
const INVALID_KEY = 'sk_live_unknown_key_02';
const RATE_LIMITED_KEY = 'sk_live_throttled_k_03';
const KEY_ID = 'key-1';
const KEY_OWNER = 'owner-1';
const KEY_TENANT = 'tenant-1';
const KEY_EXPIRES_AT = '2030-01-02T03:04:05.000Z';
const KEY_EXPIRES_AT_SECONDS = 1893553445;
const MIN_KEY_LENGTH = 16;
const MAX_KEY_LENGTH = 64;
const MIN_KEY_CHAR = 0x21;
const MAX_KEY_CHAR = 0x7e;

const ENTITY = 'Member';
const KEY_FIELD = 'id';
const SUBJECT_CLAIM = 'provider_subject';
const PROVIDER_SUBJECT = 'provider-subject-1';

interface ProfileView extends IdentityProfileDocument {
  readonly email: string;
}

type Principal = IdentityPrincipalOf<ProfileView>;

/** The problem body a test chain answers with: which builder made it, and its inputs. */
interface Problem {
  readonly family: string;
  readonly instance: string;
  readonly status?: AuthChainStatus;
  readonly detail?: string;
}

/** Log lines a chain wrote, by level. */
class RecordingLogger implements AuthChainLogger {
  readonly lines: string[] = [];

  log(message: string): void {
    this.lines.push(`log ${message}`);
  }

  warn(message: string): void {
    this.lines.push(`warn ${message}`);
  }

  error(message: string): void {
    this.lines.push(`error ${message}`);
  }

  debug(message: string): void {
    this.lines.push(`debug ${message}`);
  }
}

function principal(overrides: Partial<Principal> = {}): Principal {
  const claims = { sub: SUBJECT, [SUBJECT_CLAIM]: PROVIDER_SUBJECT };
  return {
    sub: SUBJECT,
    userId: USER_ID,
    provider: PROVIDER,
    roles: ['reader'],
    principalType: 'human',
    tenantId: null,
    localIdentityMode: 'subjectText',
    plan: '',
    claims,
    token: VALID_TOKEN,
    subject: SUBJECT,
    profile: null,
    identity: claims,
    ...overrides,
  };
}

/** The identity core's verification: each known token verifies to its principal, any other is refused. */
async function verifyIdentityToken(token: string): Promise<Principal> {
  if (token === VALID_TOKEN) {
    return principal();
  }
  if (token === PROJECTED_TOKEN) {
    return principal({ userId: '', localIdentityMode: 'projected', token });
  }
  if (token === PARTNER_TOKEN) {
    return principal({ provider: OTHER_PROVIDER, token });
  }
  if (token === CONFIG_ERROR_TOKEN) {
    throw new Error('Identity provider plan not found');
  }
  throw new IdentityVerificationError(REASON_BAD_SIGNATURE);
}

class RevocationRefusedError extends Error {
  constructor(readonly reasonCode: string) {
    super(reasonCode);
  }
}

class RevocationUnavailableError extends Error {
  readonly reasonCode = REASON_REVOCATION_UNAVAILABLE;
}

/** A revocation check over a revoked-token list; `unavailable` makes every status undeterminable. */
class RevocationList {
  readonly revoked = new Set<string>();
  unavailable = false;
  failure: Error | null = null;
  checked = 0;

  revocation(): AuthChainRevocation<ProfileView> {
    return {
      assertNotRevoked: async (_principal: Principal, token: string): Promise<void> => {
        this.checked += 1;
        if (this.failure !== null) {
          throw this.failure;
        }
        if (this.unavailable) {
          throw new RevocationUnavailableError();
        }
        if (this.revoked.has(token)) {
          throw new RevocationRefusedError(REASON_TOKEN_REVOKED);
        }
      },
      refusedError: RevocationRefusedError,
      unavailableError: RevocationUnavailableError,
      retryAfterSeconds: REVOCATION_RETRY_AFTER_SECONDS,
    };
  }
}

class VerifierUnavailableError extends Error {}

/** An API-key store keyed by key hash; records every hash it was asked to verify. */
class ApiKeyStore {
  readonly verified: Array<[string, string]> = [];
  readonly outcomes = new Map<string, ApiKeyOutcome>([
    [
      sha256(VALID_KEY),
      { outcome: 'ok', keyId: KEY_ID, ownerId: KEY_OWNER, tenantId: KEY_TENANT, scopes: ['orders:read', 'unmapped'], expiresAt: KEY_EXPIRES_AT },
    ],
    [sha256(RATE_LIMITED_KEY), { outcome: 'rateLimited', retryAfterSeconds: RATE_LIMIT_RETRY_AFTER_SECONDS }],
  ]);
  failure: Error | null = null;

  apiKeys(): AuthChainApiKeys {
    return {
      providers: [
        { name: KEY_PROVIDER, header: KEY_HEADER, roleMappings: { 'orders:read': 'reader', 'orders:write': 'writer' } },
        { name: OTHER_KEY_PROVIDER, header: OTHER_KEY_HEADER, roleMappings: {} },
      ],
      principalType: KEY_PRINCIPAL_TYPE,
      keyBounds: { minLength: MIN_KEY_LENGTH, maxLength: MAX_KEY_LENGTH, minCharCode: MIN_KEY_CHAR, maxCharCode: MAX_KEY_CHAR },
      verifyPresentedKeyHash: async (provider: string, keyHash: string): Promise<ApiKeyOutcome> => {
        this.verified.push([provider, keyHash]);
        if (this.failure !== null) {
          throw this.failure;
        }
        return this.outcomes.get(keyHash) ?? { outcome: 'invalid' };
      },
      verifierUnavailableError: VerifierUnavailableError,
    };
  }
}

/** A profile store holding rows in memory, and the metadata writes the write-back made. */
class WriteBackRecorder {
  readonly rows: Array<Record<string, unknown>> = [];
  readonly writes: Array<[string, string, string, string]> = [];
  bound = true;

  writeBack(calls: ReadonlyArray<WriteBackCall>): AuthChainWriteBack {
    const store: WriteBackStore = {
      findOne: async (entityName: string, where: Record<string, string>): Promise<object | null> => {
        if (entityName !== ENTITY) {
          return null;
        }
        return this.rows.find((row) => Object.entries(where).every(([key, value]) => row[key] === value)) ?? null;
      },
    };
    return {
      calls,
      subjectClaim: SUBJECT_CLAIM,
      openStore: () => (this.bound ? store : null),
      writeUserMetadata: async (
        provider: string,
        providerSubject: string,
        key: string,
        value: string,
      ): Promise<void> => {
        this.writes.push([provider, providerSubject, key, value]);
      },
    };
  }
}

function sha256(text: string): string {
  return createHash('sha256').update(text, 'utf8').digest('hex');
}

function chain(overrides: Partial<AuthChainOptions<ProfileView, Problem>> = {}): {
  readonly chain: AuthChain<ProfileView, Problem>;
  readonly logger: RecordingLogger;
} {
  const logger = new RecordingLogger();
  const options: AuthChainOptions<ProfileView, Problem> = {
    reasons: REASONS,
    verifyIdentityToken,
    problems: {
      revocationUnavailable: (instance: string): Problem => ({ family: 'revocation-unavailable', instance }),
      forStatus: (status: AuthChainStatus, instance: string, detail: string): Problem => ({
        family: 'status',
        instance,
        status,
        detail,
      }),
    },
    loadIdentityProfile: null,
    revocation: null,
    apiKeys: null,
    writeBack: null,
    logger,
    ...overrides,
  };
  return { chain: createAuthChain(options), logger };
}

/** The status and reason code *step* was refused with. */
async function refusal(step: Promise<unknown>): Promise<[AuthChainStatus, string]> {
  try {
    await step;
  } catch (err) {
    if (err instanceof AuthChainError) {
      return [err.status, err.reasonCode];
    }
    throw err;
  }
  throw new Error('expected the step to be refused, but it passed');
}

function bearer(token: string): RequestHeaders {
  return { authorization: `Bearer ${token}` };
}

describe('no credential', () => {
  it('refuses a missing Authorization header with 401', async () => {
    const { chain: subject, logger } = chain();

    expect(await refusal(subject.authenticateBearer(undefined))).toEqual([401, REASONS.missingToken]);
    expect(logger.lines).toContain(`warn identity_auth_failed reason_code=${REASONS.missingToken}`);
  });

  it('refuses an Authorization header of another scheme or without a token', async () => {
    const { chain: subject } = chain();

    expect(await refusal(subject.authenticateBearer('Basic dXNlcjpwYXNz'))).toEqual([401, REASONS.missingToken]);
    expect(await refusal(subject.authenticateBearer('Bearer'))).toEqual([401, REASONS.missingToken]);
  });

  it('refuses a route request presenting nothing, and two differing Authorization headers', async () => {
    const { chain: subject } = chain();

    expect(await refusal(subject.authenticateRouteRequest({}, []))).toEqual([401, REASONS.missingToken]);
    const twice: RequestHeaders = { Authorization: [`Bearer ${VALID_TOKEN}`, `Bearer ${PARTNER_TOKEN}`] };
    expect(await refusal(subject.authenticateRouteRequest(twice, []))).toEqual([401, REASONS.missingToken]);
  });

  it('treats nothing presented as anonymous under auth(optional)', async () => {
    const { chain: subject } = chain();

    expect(await subject.authenticateOptionalBearer(undefined)).toBeUndefined();
    expect(await subject.authenticateOptionalBearer(null)).toBeUndefined();
    expect(await subject.authenticateOptionalRouteRequest({}, [])).toBeUndefined();
  });
});

describe('an invalid credential', () => {
  it('refuses a token the identity core refuses with its code', async () => {
    const { chain: subject, logger } = chain();

    expect(await refusal(subject.authenticateToken(BAD_SIGNATURE_TOKEN))).toEqual([401, REASON_BAD_SIGNATURE]);
    expect(logger.lines).toContain(`warn identity_auth_failed reason_code=${REASON_BAD_SIGNATURE}`);
  });

  it('refuses under the provider-config-error code when verification fails for a deployment defect', async () => {
    const { chain: subject, logger } = chain();

    expect(await refusal(subject.authenticateToken(CONFIG_ERROR_TOKEN))).toEqual([401, REASONS.providerConfigError]);
    expect(logger.lines).toContain(`error identity_auth_config_error reason_code=${REASONS.providerConfigError}`);
  });

  it('never treats a presented but invalid credential as anonymous', async () => {
    const { chain: subject } = chain();

    expect(await refusal(subject.authenticateOptionalBearer(`Bearer ${BAD_SIGNATURE_TOKEN}`))).toEqual([
      401,
      REASON_BAD_SIGNATURE,
    ]);
    expect(await refusal(subject.authenticateOptionalRouteRequest(bearer(BAD_SIGNATURE_TOKEN), []))).toEqual([
      401,
      REASON_BAD_SIGNATURE,
    ]);
  });
});

describe('the bearer chain', () => {
  it('returns the verified principal of a valid token, whatever the header casing', async () => {
    const { chain: subject, logger } = chain();

    expect(await subject.authenticateBearer(`Bearer ${VALID_TOKEN}`)).toEqual(principal());
    expect(await subject.authenticateRouteRequest({ AUTHORIZATION: `Bearer ${VALID_TOKEN}` }, [])).toEqual(principal());
    expect(await subject.authenticateOptionalRouteRequest(bearer(VALID_TOKEN), [])).toEqual(principal());
    expect(logger.lines).toContain(`debug identity_token_verified provider=${PROVIDER}`);
  });

  it('accepts one Authorization value sent twice', async () => {
    const { chain: subject } = chain();
    const twice: RequestHeaders = { authorization: [`Bearer ${VALID_TOKEN}`, `Bearer ${VALID_TOKEN}`] };

    expect(await subject.authenticateRouteRequest(twice, [])).toEqual(principal());
  });
});

describe('a projected-mode principal', () => {
  it('takes its user id and profile from the profile store', async () => {
    const profile: ProfileView = { profileId: 'profile-7', email: 'member@example.test' };
    const { chain: subject } = chain({ loadIdentityProfile: async () => profile });

    const resolved = await subject.authenticateToken(PROJECTED_TOKEN);

    expect(resolved.userId).toBe('profile-7');
    expect(resolved.profile).toEqual(profile);
  });

  it('is denied with 403 when its profile cannot be resolved', async () => {
    const { chain: subject, logger } = chain({ loadIdentityProfile: async () => null });

    expect(await refusal(subject.authenticateToken(PROJECTED_TOKEN))).toEqual([403, REASONS.profileUnavailable]);
    expect(logger.lines).toContain(
      `warn identity_auth_failed reason_code=${REASONS.profileUnavailable} provider=${PROVIDER}`,
    );
  });

  it('is denied with 403 when the service has no profile store', async () => {
    const { chain: subject } = chain();

    expect(await refusal(subject.authenticateToken(PROJECTED_TOKEN))).toEqual([403, REASONS.profileUnavailable]);
  });
});

describe('revocation', () => {
  it('passes a credential that is not revoked', async () => {
    const revocations = new RevocationList();
    const { chain: subject } = chain({ revocation: revocations.revocation() });

    expect(await subject.authenticateToken(VALID_TOKEN)).toEqual(principal());
    expect(revocations.checked).toBe(1);
  });

  it('refuses a revoked token with 401 before projecting its profile', async () => {
    const revocations = new RevocationList();
    revocations.revoked.add(PROJECTED_TOKEN);
    let projected = 0;
    const { chain: subject } = chain({
      revocation: revocations.revocation(),
      loadIdentityProfile: async () => {
        projected += 1;
        return null;
      },
    });

    expect(await refusal(subject.authenticateToken(PROJECTED_TOKEN))).toEqual([401, REASON_TOKEN_REVOKED]);
    expect(projected).toBe(0);
  });

  it('answers 503 with Retry-After and the revocation problem when the status cannot be determined', async () => {
    const revocations = new RevocationList();
    revocations.unavailable = true;
    const { chain: subject } = chain({ revocation: revocations.revocation() });

    const failure = await subject.authenticateToken(VALID_TOKEN).catch((err: unknown) => err);

    expect(failure).toBeInstanceOf(AuthChainRevocationUnavailableError);
    const unavailable = failure as AuthChainRevocationUnavailableError;
    expect([unavailable.status, unavailable.reasonCode]).toEqual([503, REASON_REVOCATION_UNAVAILABLE]);
    expect(authChainFailureHeaders(unavailable)).toEqual({ 'Retry-After': String(REVOCATION_RETRY_AFTER_SECONDS) });
    expect(subject.authChainProblemBody(unavailable, INSTANCE)).toEqual({ family: 'revocation-unavailable', instance: INSTANCE });
  });

  it('lets any other failure of the check propagate', async () => {
    const revocations = new RevocationList();
    revocations.failure = new Error('store driver crashed');
    const { chain: subject } = chain({ revocation: revocations.revocation() });

    await expect(subject.authenticateToken(VALID_TOKEN)).rejects.toThrow('store driver crashed');
    await expect(subject.authenticateToken(VALID_TOKEN)).rejects.not.toBeInstanceOf(AuthChainError);
  });
});

describe('the API-key chain', () => {
  function keyChain(): { readonly chain: AuthChain<ProfileView, Problem>; readonly store: ApiKeyStore; readonly logger: RecordingLogger } {
    const store = new ApiKeyStore();
    const built = chain({ apiKeys: store.apiKeys() });
    return { chain: built.chain, store, logger: built.logger };
  }

  it('resolves a verified key to its principal, sending only the key hash', async () => {
    const { chain: subject, store } = keyChain();

    const resolved = await subject.authenticateRouteRequest({ [KEY_HEADER]: VALID_KEY }, [KEY_PROVIDER]);

    expect(store.verified).toEqual([[KEY_PROVIDER, sha256(VALID_KEY)]]);
    expect(resolved).toEqual({
      sub: KEY_ID,
      userId: KEY_OWNER,
      provider: KEY_PROVIDER,
      roles: ['reader'],
      principalType: KEY_PRINCIPAL_TYPE,
      tenantId: KEY_TENANT,
      localIdentityMode: 'subjectText',
      plan: '',
      claims: { exp: KEY_EXPIRES_AT_SECONDS },
      token: null,
      subject: KEY_ID,
      profile: null,
      identity: { exp: KEY_EXPIRES_AT_SECONDS },
    });
  });

  it('carries no expiry claim for a key that does not expire', async () => {
    const { chain: subject, store } = keyChain();
    store.outcomes.set(sha256(VALID_KEY), {
      outcome: 'ok', keyId: KEY_ID, ownerId: KEY_OWNER, tenantId: null, scopes: [], expiresAt: null,
    });

    const resolved = await subject.resolveApiKeyPrincipal({ [KEY_HEADER]: VALID_KEY }, [KEY_PROVIDER]);

    expect(resolved.claims).toEqual({});
    expect(resolved.roles).toEqual([]);
  });

  it('refuses ambiguous credentials with 401 before any verification', async () => {
    const { chain: subject, store } = keyChain();
    const both = [KEY_PROVIDER, OTHER_KEY_PROVIDER];

    expect(await refusal(subject.resolveApiKeyPrincipal({ ...bearer(VALID_TOKEN), [KEY_HEADER]: VALID_KEY }, both))).toEqual([
      401,
      REASON_API_KEY_AMBIGUOUS,
    ]);
    expect(await refusal(subject.resolveApiKeyPrincipal({ [KEY_HEADER]: [VALID_KEY, INVALID_KEY] }, both))).toEqual([
      401,
      REASON_API_KEY_AMBIGUOUS,
    ]);
    expect(
      await refusal(subject.resolveApiKeyPrincipal({ [KEY_HEADER]: VALID_KEY, [OTHER_KEY_HEADER]: VALID_KEY }, both)),
    ).toEqual([401, REASON_API_KEY_AMBIGUOUS]);
    expect(store.verified).toEqual([]);
  });

  it('refuses a key outside the presented-key bounds with 401 before hashing it', async () => {
    const { chain: subject, store } = keyChain();
    const outOfBounds = ['short', 'k'.repeat(MAX_KEY_LENGTH + 1), 'sk_live_with space_00', 'sk_live_tab\there_000', 'sk_live_é_000000000'];

    for (const key of outOfBounds) {
      expect(await refusal(subject.resolveApiKeyPrincipal({ [KEY_HEADER]: key }, [KEY_PROVIDER]))).toEqual([
        401,
        'api_key_out_of_bounds',
      ]);
    }
    expect(store.verified).toEqual([]);
  });

  it('refuses a key the store does not verify with 401', async () => {
    const { chain: subject } = keyChain();

    expect(await refusal(subject.resolveApiKeyPrincipal({ [KEY_HEADER]: INVALID_KEY }, [KEY_PROVIDER]))).toEqual([
      401,
      'api_key_invalid',
    ]);
  });

  it('answers a rate-limited key with 429 and Retry-After', async () => {
    const { chain: subject } = keyChain();

    const failure = await subject.resolveApiKeyPrincipal({ [KEY_HEADER]: RATE_LIMITED_KEY }, [KEY_PROVIDER]).catch((err: unknown) => err);

    expect(failure).toBeInstanceOf(AuthChainRateLimitedError);
    const limited = failure as AuthChainRateLimitedError;
    expect([limited.status, limited.reasonCode]).toEqual([429, 'api_key_rate_limited']);
    expect(authChainFailureHeaders(limited)).toEqual({ 'Retry-After': String(RATE_LIMIT_RETRY_AFTER_SECONDS) });
  });

  it('fails closed with 503 when verification cannot complete', async () => {
    const { chain: subject, store, logger } = keyChain();
    store.failure = new VerifierUnavailableError('store unreachable');

    expect(await refusal(subject.resolveApiKeyPrincipal({ [KEY_HEADER]: VALID_KEY }, [KEY_PROVIDER]))).toEqual([
      503,
      'api_key_verifier_unavailable',
    ]);
    expect(logger.lines).toContain(`error identity_auth_failed provider=${KEY_PROVIDER} reason_code=api_key_verifier_unavailable`);
  });

  it('lets any other verification failure propagate', async () => {
    const { chain: subject, store } = keyChain();
    store.failure = new Error('dispatch defect');

    await expect(subject.resolveApiKeyPrincipal({ [KEY_HEADER]: VALID_KEY }, [KEY_PROVIDER])).rejects.toThrow('dispatch defect');
  });

  it('never reads the key header of a provider the route does not admit', async () => {
    const { chain: subject, store } = keyChain();

    expect(await refusal(subject.authenticateRouteRequest({ [OTHER_KEY_HEADER]: VALID_KEY }, [KEY_PROVIDER]))).toEqual([
      401,
      REASONS.missingToken,
    ]);
    expect(await subject.authenticateRouteApiKey({ [OTHER_KEY_HEADER]: VALID_KEY }, [PROVIDER, KEY_PROVIDER])).toBeUndefined();
    expect(store.verified).toEqual([]);
  });

  it('runs the bearer chain when no admitted key header is presented', async () => {
    const { chain: subject } = keyChain();

    expect(await subject.authenticateRouteRequest(bearer(VALID_TOKEN), [KEY_PROVIDER])).toEqual(principal());
    expect(await subject.authenticateOptionalRouteRequest({}, [KEY_PROVIDER])).toBeUndefined();
  });

  it('reads the API-key providers of a route allow-list and the keys a request presents', async () => {
    const { chain: subject } = keyChain();

    expect(subject.routeApiKeyProviders([PROVIDER, OTHER_KEY_PROVIDER, KEY_PROVIDER])).toEqual([OTHER_KEY_PROVIDER, KEY_PROVIDER]);
    expect(subject.presentsRouteApiKey({ [KEY_HEADER]: VALID_KEY }, [PROVIDER, KEY_PROVIDER])).toBe(true);
    expect(subject.presentsRouteApiKey(bearer(VALID_TOKEN), [PROVIDER, KEY_PROVIDER])).toBe(false);
    expect(subject.hasAdmittedApiKeyHeader({ 'X-Api-Key': VALID_KEY }, [KEY_PROVIDER])).toBe(true);
    expect((await subject.authenticateRouteApiKey({ [KEY_HEADER]: VALID_KEY }, [PROVIDER, KEY_PROVIDER]))?.sub).toBe(KEY_ID);
    expect((await subject.authenticateOptionalRouteRequest({ [KEY_HEADER]: VALID_KEY }, [KEY_PROVIDER]))?.sub).toBe(KEY_ID);
  });

  it('refuses a provider name the service does not admit as a generation drift', () => {
    const { chain: subject } = keyChain();

    expect(() => subject.hasAdmittedApiKeyHeader({}, ['unknown-keys'])).toThrow(
      `'unknown-keys' is not an API-key provider this service admits. Admitted providers: ${KEY_PROVIDER}, ${OTHER_KEY_PROVIDER}.`,
    );
  });
});

describe('a service with no API-key chain', () => {
  it('admits no key and runs the bearer chain', async () => {
    const { chain: subject } = chain();

    expect(subject.routeApiKeyProviders([PROVIDER, KEY_PROVIDER])).toEqual([]);
    expect(subject.presentsRouteApiKey({ [KEY_HEADER]: VALID_KEY }, [KEY_PROVIDER])).toBe(false);
    expect(await subject.authenticateRouteApiKey({ [KEY_HEADER]: VALID_KEY }, [KEY_PROVIDER])).toBeUndefined();
    expect(await subject.authenticateRouteRequest(bearer(VALID_TOKEN), [])).toEqual(principal());
  });

  it('refuses a route that admits API-key providers as a generation drift', async () => {
    const { chain: subject } = chain();
    const drift = 'A route admits the API-key providers storefront-keys, but this service renders no API-key chain.';

    await expect(subject.authenticateRouteRequest(bearer(VALID_TOKEN), [KEY_PROVIDER])).rejects.toThrow(drift);
    await expect(subject.authenticateOptionalRouteRequest({}, [KEY_PROVIDER])).rejects.toThrow(drift);
    await expect(subject.resolveApiKeyPrincipal({ [KEY_HEADER]: VALID_KEY }, [KEY_PROVIDER])).rejects.toThrow(drift);
  });
});

describe('the identity write-back', () => {
  const CALLS: ReadonlyArray<WriteBackCall> = [
    { provider: PROVIDER, entity: ENTITY, keyField: KEY_FIELD, field: 'tier', valueKind: 'enum', attributesTenant: false },
    { provider: PROVIDER, entity: ENTITY, keyField: KEY_FIELD, field: 'orgId', valueKind: 'uuid', attributesTenant: true },
    { provider: OTHER_PROVIDER, entity: ENTITY, keyField: KEY_FIELD, field: 'tier', valueKind: 'text', attributesTenant: false },
  ];

  it("writes each field of the principal's provider and takes the tenant from the row", async () => {
    const recorder = new WriteBackRecorder();
    recorder.rows.push({ id: USER_ID, tier: 'gold', orgId: 'A1B2C3D4-0000-4000-8000-000000000001' });
    const { chain: subject } = chain({ writeBack: recorder.writeBack(CALLS) });

    const resolved = await subject.authenticateToken(VALID_TOKEN);

    expect(recorder.writes).toEqual([
      [PROVIDER, PROVIDER_SUBJECT, 'tier', 'gold'],
      [PROVIDER, PROVIDER_SUBJECT, 'orgId', 'a1b2c3d4-0000-4000-8000-000000000001'],
    ]);
    expect(resolved.tenantId).toBe('a1b2c3d4-0000-4000-8000-000000000001');
  });

  it('writes nothing and names no tenant for a caller with no row', async () => {
    const recorder = new WriteBackRecorder();
    const { chain: subject } = chain({ writeBack: recorder.writeBack(CALLS) });

    const resolved = await subject.authenticateToken(VALID_TOKEN);

    expect(recorder.writes).toEqual([]);
    expect(resolved.tenantId).toBeNull();
  });

  it('writes nothing when no profile store is bound', async () => {
    const recorder = new WriteBackRecorder();
    recorder.rows.push({ id: USER_ID, tier: 'gold', orgId: 'a1b2c3d4-0000-4000-8000-000000000001' });
    recorder.bound = false;
    const { chain: subject, logger } = chain({ writeBack: recorder.writeBack(CALLS) });

    const resolved = await subject.authenticateToken(VALID_TOKEN);

    expect(recorder.writes).toEqual([]);
    expect(resolved.tenantId).toBeNull();
    expect(logger.lines).toContain(`warn identity_write_back_entity_manager_unbound provider=${PROVIDER}`);
  });

  it('leaves the principal unchanged when its provider has no write-back call', async () => {
    const recorder = new WriteBackRecorder();
    const { chain: subject } = chain({ writeBack: recorder.writeBack(CALLS.slice(0, 1)) });

    expect(await subject.authenticateToken(PARTNER_TOKEN)).toEqual(principal({ provider: OTHER_PROVIDER, token: PARTNER_TOKEN }));
    expect(recorder.writes).toEqual([]);
  });

  it('fails loud when the verified token lacks the declared subject claim', async () => {
    const recorder = new WriteBackRecorder();
    const { chain: subject } = chain({
      writeBack: recorder.writeBack(CALLS),
      verifyIdentityToken: async () => principal({ claims: { sub: SUBJECT } }),
    });

    await expect(subject.authenticateToken(VALID_TOKEN)).rejects.toThrow(`requires the '${SUBJECT_CLAIM}' claim`);
  });

  it('serializes each value kind to its canonical claim text', () => {
    expect(writeBackText('Gold', 'text')).toBe('Gold');
    expect(writeBackText('GOLD', 'enum')).toBe('GOLD');
    expect(writeBackText('A1B2C3D4-0000-4000-8000-00000000000F', 'uuid')).toBe('a1b2c3d4-0000-4000-8000-00000000000f');
    expect(writeBackText(new Date('2026-10-19T23:59:59.000Z'), 'date')).toBe('2026-10-19');
    expect(writeBackText('2026-10-19', 'date')).toBe('2026-10-19');
    expect(writeBackText(new Date('2026-10-19T08:00:00Z'), 'date_time')).toBe('2026-10-19T08:00:00.000Z');
    expect(writeBackText('12.500', 'decimal')).toBe('12.5');
    expect(writeBackText('-0.00', 'decimal')).toBe('0');
    expect(writeBackText(1e21, 'decimal')).toBe('1000000000000000000000');
    expect(writeBackText(42, 'integer')).toBe('42');
    expect(writeBackText(0, 'boolean')).toBe('false');
    expect(writeBackText(true, 'boolean')).toBe('true');
  });

  it('refuses a value its kind has no serialization for', () => {
    expect(() => writeBackText('19/10/2026', 'date')).toThrow('expected an ISO 8601 calendar date');
    expect(() => writeBackText('1e5', 'decimal')).toThrow('it is not a plain decimal number');
  });
});

describe('the authorization checks', () => {
  it('admits a principal whose provider, role and type the route allows', () => {
    const { chain: subject } = chain();

    expect(() => subject.requireProviders(principal(), [OTHER_PROVIDER, PROVIDER])).not.toThrow();
    expect(() => subject.requireRoles(principal(), ['writer', 'reader'])).not.toThrow();
    expect(() => subject.requirePrincipalTypes(principal(), ['human'])).not.toThrow();
  });

  it('denies a principal the route does not allow with 403', async () => {
    const { chain: subject } = chain();

    expect(await refusal(Promise.resolve().then(() => subject.requireProviders(principal(), [OTHER_PROVIDER])))).toEqual([
      403,
      REASONS.providerNotAllowed,
    ]);
    expect(await refusal(Promise.resolve().then(() => subject.requireRoles(principal(), ['admin'])))).toEqual([
      403,
      REASONS.roleDenied,
    ]);
    expect(await refusal(Promise.resolve().then(() => subject.requirePrincipalTypes(principal(), ['machine'])))).toEqual([
      403,
      REASONS.principalTypeMismatch,
    ]);
  });

  it('forwards the bearer token of a JWT principal and never an API-key principal', () => {
    const { chain: subject, logger } = chain();

    expect(subject.bearerTokenOrForbidden(principal())).toBe(VALID_TOKEN);
    expect(() => subject.bearerTokenOrForbidden(principal({ token: null }))).toThrow(ForbiddenException);
    expect(logger.lines).toContain(`warn identity_auth_failed reason_code=${REASONS.noForwardableToken} provider=${PROVIDER}`);
  });
});

describe('the refusal shape', () => {
  it('answers each status with an opaque detail, never the reason code', () => {
    const details = ([401, 403, 429, 503] as const).map((status) => authChainFailureDetail(new AuthChainError(status, 'secret_reason')));

    expect(details).toEqual(['Authentication required', 'Insufficient permissions', 'Too many requests', 'Service temporarily unavailable']);
  });

  it('sends Retry-After only for a rate-limited key or an undeterminable revocation status', () => {
    expect(authChainFailureHeaders(new AuthChainError(401, REASONS.missingToken))).toEqual({});
    expect(authChainFailureHeaders(new AuthChainError(503, 'api_key_verifier_unavailable'))).toEqual({});
    expect(authChainFailureHeaders(new AuthChainRevocationUnavailableError(REASON_REVOCATION_UNAVAILABLE, 5))).toEqual({ 'Retry-After': '5' });
  });

  it('answers a failed step with the generic problem of its status', () => {
    const { chain: subject } = chain();

    expect(subject.authChainProblemBody(new AuthChainError(403, REASONS.roleDenied), INSTANCE)).toEqual({
      family: 'status',
      instance: INSTANCE,
      status: 403,
      detail: 'Insufficient permissions',
    });
  });
});
