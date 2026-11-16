/**
 * Jest spec of the identity runtime module (`src/_runtime/identity.ts`).
 *
 * Tokens are signed with real RSA keys and verified against a key set served over
 * HTTP from this process, so each refusal path runs through `jose` exactly as it does
 * in the service: expired, wrong issuer, wrong audience, bad signature, unknown key id,
 * key-set refresh failure, plus the plan-load and plan-content refusals.
 *
 * Shipped by cruftfree-codegen-typescript-core and emitted verbatim. Do not edit manually.
 */
import { exportJWK, exportPKCS8, generateKeyPair, jwtVerify, SignJWT } from 'jose';
import type { JWK, KeyLike } from 'jose';
import * as fs from 'node:fs';
import * as http from 'node:http';
import type { AddressInfo } from 'node:net';
import * as os from 'node:os';
import * as path from 'node:path';
import { createIdentityCore, IdentityVerificationError } from '../../src/_runtime/identity';
import type {
  IdentityCore,
  IdentityProfileDocument,
  IdentityReasonCodes,
  IdentityRuntimeLogger,
} from '../../src/_runtime/identity';

const REASONS: IdentityReasonCodes = {
  malformedToken: 'test_malformed_token',
  expiredToken: 'test_expired_token',
  badSignature: 'test_bad_signature',
  issuerMismatch: 'test_issuer_mismatch',
  audienceMismatch: 'test_audience_mismatch',
  jwksRefreshFailed: 'test_jwks_refresh_failed',
  providerMismatch: 'test_provider_mismatch',
  mfaRequired: 'test_mfa_required',
};

const SCHEMA_VERSION = 1;
const ALGORITHM = 'RS256';
const SIGNING_KID = 'signing-key';
const ISSUER = 'https://issuer.example.test/realms/shop';
const AUDIENCE = 'shop-api';
const PROVIDER = 'customer';
const SUBJECT = '377787792123494405';
/** The namespace every CruftFree target derives deterministic local user ids under. */
const NAMESPACE = 'c9a255a1-350b-4414-beb9-7f06f7dfd92d';
/** uuidv5(NAMESPACE, `${PROVIDER}:${SUBJECT}`): pinned across every target language. */
const PINNED_LOCAL_USER_ID = '657f1b4d-fa7e-577d-a02b-80a8598128b2';
const SECONDS_PER_MINUTE = 60;

/** Log lines a core wrote, by level. */
class RecordingLogger implements IdentityRuntimeLogger {
  readonly lines: string[] = [];

  log(message: string): void {
    this.lines.push(`log ${message}`);
  }

  warn(message: string): void {
    this.lines.push(`warn ${message}`);
  }

  debug(message: string): void {
    this.lines.push(`debug ${message}`);
  }
}

let signingKey: KeyLike;
let strangerKey: KeyLike;
let keySetServer: http.Server;
let jwksUri: string;
let closedJwksUri: string;
let planDir: string;

function listen(server: http.Server): Promise<string> {
  return new Promise((resolve) => {
    server.listen(0, '127.0.0.1', () => {
      resolve(`http://127.0.0.1:${(server.address() as AddressInfo).port}/jwks`);
    });
  });
}

/** Stop *server*, dropping the kept-alive connections the key-set fetches left open. */
function close(server: http.Server): Promise<void> {
  return new Promise((resolve) => {
    server.close(() => resolve());
    server.closeAllConnections();
  });
}

beforeAll(async () => {
  const signing = await generateKeyPair(ALGORITHM);
  const stranger = await generateKeyPair(ALGORITHM);
  signingKey = signing.privateKey;
  strangerKey = stranger.privateKey;
  const publicJwk: JWK = { ...(await exportJWK(signing.publicKey)), kid: SIGNING_KID, alg: ALGORITHM, use: 'sig' };
  const body = JSON.stringify({ keys: [publicJwk] });
  keySetServer = http.createServer((_request, response) => {
    response.writeHead(200, { 'content-type': 'application/json' });
    response.end(body);
  });
  jwksUri = await listen(keySetServer);
  const closed = http.createServer();
  closedJwksUri = await listen(closed);
  await close(closed);
  planDir = fs.mkdtempSync(path.join(os.tmpdir(), 'identity-spec-'));
});

afterAll(async () => {
  await close(keySetServer);
  fs.rmSync(planDir, { recursive: true, force: true });
});

/** A JWT provider entry of the plan; *overrides* replace its members. */
function jwtProvider(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    credential: 'jwt',
    name: PROVIDER,
    providerType: 'oidc',
    audience: 'external',
    mode: 'jwks',
    principalType: 'human',
    issuer: ISSUER,
    jwksUri,
    allowedAlgorithms: [ALGORITHM],
    allowedAudiences: [AUDIENCE],
    allowedAudienceRefs: [],
    jwksCacheTtlSeconds: 300,
    revocation: { mode: 'none', tokenIdClaim: 'jti' },
    roleSource: { claimPath: 'realm_access.roles' },
    roleMappings: { 'shop-admin': 'admin' },
    attributeMappings: {},
    localIdentity: { mode: 'deterministicUuid5', namespace: NAMESPACE },
    secretRefs: {},
    ...overrides,
  };
}

let planCounter = 0;

/** Write *plan* to its own file and return its path. */
function writePlan(plan: Record<string, unknown>): string {
  planCounter += 1;
  const planPath = path.join(planDir, `plan-${planCounter}.json`);
  fs.writeFileSync(planPath, JSON.stringify(plan), 'utf-8');
  return planPath;
}

/** A plan holding *providers*, at the supported schema version unless overridden. */
function plan(providers: Record<string, unknown>, schemaVersion: number = SCHEMA_VERSION): Record<string, unknown> {
  return { schemaVersion, application: 'shop', environment: 'test', providers };
}

/** A core over *planPath*, reading application settings from *settings*. */
function coreFor(
  planPath: string,
  settings: Record<string, string> = {},
  logger: IdentityRuntimeLogger = new RecordingLogger(),
): IdentityCore<IdentityProfileDocument> {
  return createIdentityCore<IdentityProfileDocument>({
    reasons: REASONS,
    planSchemaVersion: SCHEMA_VERSION,
    bundledPlanPath: planPath,
    bakedPlanPath: null,
    lateBoundSetting: (name) => settings[name] ?? null,
    logger,
  });
}

/** A core whose plan holds the one *provider*. */
function providerCore(provider: Record<string, unknown> = jwtProvider()): IdentityCore<IdentityProfileDocument> {
  return coreFor(writePlan(plan({ [PROVIDER]: provider })));
}

interface TokenShape {
  readonly issuer?: string;
  readonly audience?: string;
  readonly expiresAt?: number;
  readonly kid?: string;
  readonly key?: KeyLike;
  readonly claims?: Record<string, unknown>;
}

function nowSeconds(): number {
  return Math.floor(Date.now() / 1000);
}

async function token(shape: TokenShape = {}): Promise<string> {
  return new SignJWT({ realm_access: { roles: ['shop-admin', 'reader'] }, plan: ' gold ', ...shape.claims })
    .setProtectedHeader({ alg: ALGORITHM, kid: shape.kid ?? SIGNING_KID })
    .setSubject(SUBJECT)
    .setIssuer(shape.issuer ?? ISSUER)
    .setAudience(shape.audience ?? AUDIENCE)
    .setIssuedAt()
    .setExpirationTime(shape.expiresAt ?? nowSeconds() + 5 * SECONDS_PER_MINUTE)
    .sign(shape.key ?? signingKey);
}

/** The reason code *verification* was refused with. */
async function refusal(verification: Promise<unknown>): Promise<string> {
  try {
    await verification;
  } catch (err) {
    if (err instanceof IdentityVerificationError) {
      return err.reasonCode;
    }
    throw err;
  }
  throw new Error('expected the token to be refused, but it verified');
}

describe('verifyIdentityToken', () => {
  it('accepts a valid token and derives the principal from the plan', async () => {
    const principal = await providerCore().verifyIdentityToken(await token());

    expect(principal.provider).toBe(PROVIDER);
    expect(principal.sub).toBe(SUBJECT);
    expect(principal.subject).toBe(SUBJECT);
    expect(principal.userId).toBe(PINNED_LOCAL_USER_ID);
    expect(principal.roles).toEqual(['admin', 'reader']);
    expect(principal.plan).toBe('gold');
    expect(principal.localIdentityMode).toBe('deterministicUuid5');
    expect(principal.tenantId).toBeNull();
    expect(principal.profile).toBeNull();
    expect(principal.identity).toEqual(principal.claims);
  });

  describe('the shape of the role claim', () => {
    const ZITADEL_ROLES_CLAIM = 'urn:zitadel:iam:org:project:roles';
    const zitadel = (): Record<string, unknown> => jwtProvider({
      roleSource: { claimPath: ZITADEL_ROLES_CLAIM },
      roleMappings: { frontdesk: 'frontDesk', operators: 'operator' },
    });

    it.each([
      {
        shape: 'a map of role keys (the Zitadel default)',
        claim: { frontdesk: { '1234': 'idp.example.test' }, reader: { '1234': 'idp.example.test' } },
        roles: ['frontDesk', 'reader'],
      },
      { shape: 'a flat list of role names', claim: ['frontdesk', 'reader'], roles: ['frontDesk', 'reader'] },
      { shape: 'a string', claim: 'frontdesk', roles: [] },
      { shape: 'an empty map', claim: {}, roles: [] },
    ])('reads $shape', async ({ claim, roles }) => {
      const principal = await providerCore(zitadel()).verifyIdentityToken(
        await token({ claims: { [ZITADEL_ROLES_CLAIM]: claim } }),
      );

      expect(principal.roles).toEqual(roles);
    });

    it('grants no role when the claim is absent', async () => {
      const principal = await providerCore(zitadel()).verifyIdentityToken(await token());

      expect(principal.roles).toEqual([]);
    });
  });

  describe('Auth.identity of a provider that maps its fields', () => {
    /** Built per test: the key-set URL `jwtProvider` reads is known only once `beforeAll` ran. */
    const mapped = (): Record<string, unknown> => jwtProvider({
      attributeMappings: {
        fullName: { claimPath: 'name', guarantee: 'optional', cruftfreeType: 'String', nullable: true },
        team: { claimPath: 'org.team', guarantee: 'optional', cruftfreeType: 'String', nullable: true },
      },
    });

    it('reads a declared field through its claim path, a dotted one included', async () => {
      const claims = { name: 'Ada Byron', org: { team: 'analytics' } };
      const principal = await providerCore(mapped()).verifyIdentityToken(await token({ claims }));

      expect(principal.identity['fullName']).toBe('Ada Byron');
      expect(principal.identity['team']).toBe('analytics');
    });

    it('reads a field its claim path does not reach as null, whatever the token spells like it', async () => {
      const claims = { fullName: 'Forged Name' };
      const principal = await providerCore(mapped()).verifyIdentityToken(await token({ claims }));

      expect(principal.identity['fullName']).toBeNull();
      expect(principal.claims['fullName']).toBe('Forged Name');
    });

    it('keeps every undeclared claim under its own name', async () => {
      const principal = await providerCore(mapped()).verifyIdentityToken(await token());

      expect(principal.identity.sub).toBe(SUBJECT);
    });

    it('never shadows a claim of the token itself', async () => {
      const shadowing = jwtProvider({
        attributeMappings: { exp: { claimPath: 'name', guarantee: 'optional', cruftfreeType: 'String', nullable: true } },
      });
      const principal = await providerCore(shadowing).verifyIdentityToken(await token());

      expect(typeof principal.claims.exp).toBe('number');
    });
  });

  describe('the second-factor proof of a mfa = "required" provider', () => {
    /** Built per test: the key-set URL `jwtProvider` reads is known only once `beforeAll` ran. */
    const required = (): Record<string, unknown> => jwtProvider({
      mfaFactorProof: { claim: 'amr', provingValues: ['mfa'], source: 'token' },
    });

    it.each([
      [['pwd', 'otp', 'mfa']],
      [['mfa']],
    ])('admits a token whose amr %j lists a proving value', async (amr) => {
      const principal = await providerCore(required()).verifyIdentityToken(await token({ claims: { amr } }));

      expect(principal.claims['amr']).toEqual(amr);
    });

    it.each([
      ['absent', undefined],
      ['password only', ['pwd']],
      ['empty', []],
      ['a bare string', 'mfa'],
      ['another spelling', ['MFA']],
      ['not strings', [1, null]],
      ['an object', { mfa: true }],
    ])('refuses a token whose amr is %s', async (_label, amr) => {
      const claims = amr === undefined ? {} : { amr };

      expect(await refusal(providerCore(required()).verifyIdentityToken(await token({ claims }))))
        .toBe(REASONS.mfaRequired);
    });

    it('admits a password-only token of a provider without the proof', async () => {
      const principal = await providerCore().verifyIdentityToken(await token({ claims: { amr: ['pwd'] } }));

      expect(principal.claims['amr']).toEqual(['pwd']);
    });
  });

  describe('the second-factor proof read from the provider\'s introspection answer', () => {
    const CLIENT_ID = 'introspection-client';
    const CLIENT_KEY_ID = 'introspection-key';
    const HOST_HEADER = 'id.example.test:8085';
    const ASSERTION_TYPE = 'urn:ietf:params:oauth:client-assertion-type:jwt-bearer';
    const CACHE_SECONDS = 30;
    const PROVING = { active: true, sub: SUBJECT, amr: ['pwd', 'otp', 'mfa'] };
    const PASSWORD_ONLY = { active: true, sub: SUBJECT, amr: ['pwd'] };

    /** What the introspection server was asked, as it saw it. */
    interface Question {
      readonly host: string | undefined;
      readonly token: string | null;
    }

    let clientPublicKey: KeyLike;
    let introspectionServer: http.Server;
    let introspectionUrl: string;
    let keyFile: string;
    let strangerKeyFile: string;
    let answer: Record<string, unknown>;
    let questions: Question[];
    let rejected: number;

    /** Whether the question carries an assertion signed by the client's key (RFC 7523). */
    async function authenticated(form: URLSearchParams): Promise<boolean> {
      if (form.get('client_assertion_type') !== ASSERTION_TYPE) {
        return false;
      }
      try {
        await jwtVerify(form.get('client_assertion') ?? '', clientPublicKey, {
          issuer: CLIENT_ID,
          subject: CLIENT_ID,
          audience: ISSUER,
          algorithms: [ALGORITHM],
          requiredClaims: ['exp', 'iat', 'jti'],
        });
        return true;
      } catch {
        return false;
      }
    }

    async function writeKeyFile(name: string, key: KeyLike): Promise<string> {
      const file = path.join(planDir, name);
      fs.writeFileSync(
        file,
        JSON.stringify({ keyId: CLIENT_KEY_ID, key: await exportPKCS8(key), clientId: CLIENT_ID }),
        'utf-8',
      );
      return file;
    }

    beforeAll(async () => {
      const client = await generateKeyPair(ALGORITHM);
      clientPublicKey = client.publicKey;
      keyFile = await writeKeyFile('introspection-key.json', client.privateKey);
      strangerKeyFile = await writeKeyFile('introspection-stranger-key.json', strangerKey);
      introspectionServer = http.createServer((request, response) => {
        const chunks: Buffer[] = [];
        request.on('data', (chunk: Buffer) => chunks.push(chunk));
        request.on('end', () => {
          const form = new URLSearchParams(Buffer.concat(chunks).toString('utf-8'));
          void authenticated(form).then((asked) => {
            if (!asked) {
              rejected += 1;
              response.writeHead(401);
              response.end();
              return;
            }
            questions.push({ host: request.headers.host, token: form.get('token') });
            response.writeHead(200, { 'content-type': 'application/json' });
            response.end(JSON.stringify(answer));
          });
        });
      });
      introspectionUrl = await listen(introspectionServer);
    });

    afterAll(async () => {
      await close(introspectionServer);
    });

    beforeEach(() => {
      answer = { ...PROVING };
      questions = [];
      rejected = 0;
    });

    /** A provider whose access tokens carry no `amr`; the proof is read from the answer. */
    const asking = (
      overrides: { credentialFile?: string; cacheSeconds?: number; url?: string } = {},
    ): Record<string, unknown> => jwtProvider({
      mfaFactorProof: {
        claim: 'amr',
        provingValues: ['mfa'],
        source: 'introspection',
        introspection: {
          url: overrides.url ?? introspectionUrl,
          hostHeader: HOST_HEADER,
          credentialFile: overrides.credentialFile ?? keyFile,
          cacheSeconds: overrides.cacheSeconds ?? CACHE_SECONDS,
        },
      },
    });

    it('admits a token whose introspection answer proves a second factor, and sends the Host header', async () => {
      const bearer = await token();

      const principal = await providerCore(asking()).verifyIdentityToken(bearer);

      expect(principal.claims['amr']).toBeUndefined();
      expect(questions).toEqual([{ host: HOST_HEADER, token: bearer }]);
    });

    it.each([
      ['password only', PASSWORD_ONLY],
      ['no methods', { active: true, sub: SUBJECT }],
      ['methods that are not an array', { active: true, sub: SUBJECT, amr: 'mfa' }],
      ['an inactive session', { active: false }],
      ['an active flag that is not a boolean', { active: 'true', sub: SUBJECT, amr: ['mfa'] }],
      ['another subject', { active: true, sub: 'someone-else', amr: ['mfa'] }],
    ])('refuses a token whose introspection answer is %s', async (_label, refused) => {
      answer = { ...refused };

      expect(await refusal(providerCore(asking()).verifyIdentityToken(await token()))).toBe(REASONS.mfaRequired);
    });

    it('refuses a token when the key file holds another key than the provider knows', async () => {
      const core = providerCore(asking({ credentialFile: strangerKeyFile }));

      expect(await refusal(core.verifyIdentityToken(await token()))).toBe(REASONS.mfaRequired);
      expect(rejected).toBe(1);
    });

    it('refuses a token when the key file is missing, and asks nothing', async () => {
      const core = providerCore(asking({ credentialFile: path.join(planDir, 'absent-key.json') }));

      expect(await refusal(core.verifyIdentityToken(await token()))).toBe(REASONS.mfaRequired);
      expect(questions).toEqual([]);
    });

    it('refuses a token when the provider cannot be reached', async () => {
      const core = providerCore(asking({ url: closedJwksUri }));

      expect(await refusal(core.verifyIdentityToken(await token()))).toBe(REASONS.mfaRequired);
    });

    it.each([
      [CACHE_SECONDS, 1],
      [0, 2],
    ])('asks about a proving token once per cache time (%d seconds: %d question(s))', async (cacheSeconds, asked) => {
      const core = providerCore(asking({ cacheSeconds }));
      const bearer = await token();

      await core.verifyIdentityToken(bearer);
      await core.verifyIdentityToken(bearer);

      expect(questions).toHaveLength(asked);
    });

    it('asks again after a refusal and admits a later proof', async () => {
      answer = { ...PASSWORD_ONLY };
      const core = providerCore(asking());
      const bearer = await token();

      await refusal(core.verifyIdentityToken(bearer));
      answer = { ...PROVING };
      await core.verifyIdentityToken(bearer);

      expect(questions.map((question) => question.token)).toEqual([bearer, bearer]);
    });

    it.each([
      [
        'an introspection source without its endpoint',
        { claim: 'amr', provingValues: ['mfa'], source: 'introspection' },
        "no 'introspection' object",
      ],
      [
        'a token source that carries an endpoint',
        {
          claim: 'amr',
          provingValues: ['mfa'],
          source: 'token',
          introspection: { url: 'https://id.example.test/introspect', credentialFile: '/k.json', cacheSeconds: 1 },
        },
        "'token' source",
      ],
      ['no source', { claim: 'amr', provingValues: ['mfa'] }, "'source'"],
      [
        'an endpoint of another scheme',
        {
          claim: 'amr',
          provingValues: ['mfa'],
          source: 'introspection',
          introspection: { url: 'ftp://id.example.test/introspect', credentialFile: '/k.json', cacheSeconds: 1 },
        },
        'mfaFactorProof.introspection.url',
      ],
      [
        'a cache time above the bound',
        {
          claim: 'amr',
          provingValues: ['mfa'],
          source: 'introspection',
          introspection: { url: 'https://id.example.test/introspect', credentialFile: '/k.json', cacheSeconds: 61 },
        },
        'cacheSeconds',
      ],
      [
        'a blank key file',
        {
          claim: 'amr',
          provingValues: ['mfa'],
          source: 'introspection',
          introspection: { url: 'https://id.example.test/introspect', credentialFile: '', cacheSeconds: 1 },
        },
        'credentialFile',
      ],
      [
        'a member this runtime does not know',
        {
          claim: 'amr',
          provingValues: ['mfa'],
          source: 'introspection',
          introspection: {
            url: 'https://id.example.test/introspect',
            credentialFile: '/k.json',
            cacheSeconds: 1,
            secret: 'x',
          },
        },
        'undeclared member',
      ],
    ])('refuses a plan with %s', (_case, mfaFactorProof, problem) => {
      const core = coreFor(writePlan(plan({ [PROVIDER]: jwtProvider({ mfaFactorProof }) })));

      expect(() => core.loadIdentityPlanAtStartup()).toThrow(problem);
    });
  });

  it('refuses an expired token', async () => {
    const expired = await token({ expiresAt: nowSeconds() - 5 * SECONDS_PER_MINUTE });

    expect(await refusal(providerCore().verifyIdentityToken(expired))).toBe(REASONS.expiredToken);
  });

  it('refuses a token from an issuer no provider declares', async () => {
    const foreign = await token({ issuer: 'https://other.example.test/' });

    expect(await refusal(providerCore().verifyIdentityToken(foreign))).toBe(REASONS.providerMismatch);
  });

  it('refuses a token for another audience', async () => {
    const elsewhere = await token({ audience: 'another-api' });

    expect(await refusal(providerCore().verifyIdentityToken(elsewhere))).toBe(REASONS.audienceMismatch);
  });

  it('refuses a token whose signature the key set does not verify', async () => {
    const forged = await token({ key: strangerKey });

    expect(await refusal(providerCore().verifyIdentityToken(forged))).toBe(REASONS.badSignature);
  });

  it('refuses a token signed under a key id the key set does not hold as a key-set refresh failure, and logs the code', async () => {
    const logger = new RecordingLogger();
    const core = coreFor(writePlan(plan({ [PROVIDER]: jwtProvider() })), {}, logger);
    const unknownKid = await token({ key: strangerKey, kid: 'rotated-away' });

    expect(await refusal(core.verifyIdentityToken(unknownKid))).toBe(REASONS.jwksRefreshFailed);
    expect(logger.lines).toContain(
      `warn identity_jwks_refresh_failed provider=${PROVIDER} reason_code=${REASONS.jwksRefreshFailed}`,
    );
  });

  it('refuses every token when the key set cannot be fetched, and logs the code', async () => {
    const logger = new RecordingLogger();
    const core = coreFor(writePlan(plan({ [PROVIDER]: jwtProvider({ jwksUri: closedJwksUri }) })), {}, logger);

    expect(await refusal(core.verifyIdentityToken(await token()))).toBe(REASONS.jwksRefreshFailed);
    expect(logger.lines).toContain(
      `warn identity_jwks_refresh_failed provider=${PROVIDER} reason_code=${REASONS.jwksRefreshFailed}`,
    );
  });

  it('fetches the keys from the in-network endpoint when the plan names one', async () => {
    const core = providerCore(jwtProvider({ jwksUri: closedJwksUri, jwksFetch: { url: jwksUri } }));

    expect((await core.verifyIdentityToken(await token())).provider).toBe(PROVIDER);
  });

  it('refuses a value that is not a token', async () => {
    expect(await refusal(providerCore().verifyIdentityToken('not-a-token'))).toBe(REASONS.malformedToken);
  });

  it.each([['none'], ['HS256']])('refuses every token when the plan allows algorithm %s', async (algorithm) => {
    const core = providerCore(jwtProvider({ allowedAlgorithms: [ALGORITHM, algorithm] }));

    expect(await refusal(core.verifyIdentityToken(await token()))).toBe(REASONS.badSignature);
  });

  it('adds a late-bound audience read from the application settings', async () => {
    const provider = jwtProvider({ allowedAudiences: [], allowedAudienceRefs: ['API_CLIENT_ID'] });
    const core = coreFor(writePlan(plan({ [PROVIDER]: provider })), { API_CLIENT_ID: 'late-bound-api' });

    expect((await core.verifyIdentityToken(await token({ audience: 'late-bound-api' }))).provider).toBe(PROVIDER);
  });

  it('fails closed when a late-bound audience setting is unset', async () => {
    const provider = jwtProvider({ allowedAudiences: [], allowedAudienceRefs: ['API_CLIENT_ID'] });
    const verification = providerCore(provider).verifyIdentityToken(await token());

    await expect(verification).rejects.toThrow("declares allowedAudienceRefs entry 'API_CLIENT_ID'");
    await expect(verification).rejects.not.toBeInstanceOf(IdentityVerificationError);
  });

  it('selects, among providers sharing an issuer, the one whose audience the token carries', async () => {
    const providers = {
      admin: jwtProvider({ name: 'admin', allowedAudiences: ['admin-api'] }),
      [PROVIDER]: jwtProvider(),
    };
    const principal = await coreFor(writePlan(plan(providers))).verifyIdentityToken(await token());

    expect(principal.provider).toBe(PROVIDER);
  });

  it('leaves the user id of a projected provider to the profile store', async () => {
    const core = providerCore(jwtProvider({ localIdentity: { mode: 'projected' } }));

    expect((await core.verifyIdentityToken(await token())).userId).toBe('');
  });

  it('uses the raw subject under subjectText', async () => {
    const core = providerCore(jwtProvider({ localIdentity: { mode: 'subjectText' } }));

    expect((await core.verifyIdentityToken(await token())).userId).toBe(SUBJECT);
  });
});

describe('the identity provider plan', () => {
  it('loads at startup from the bundled path', () => {
    const logger = new RecordingLogger();
    coreFor(writePlan(plan({ [PROVIDER]: jwtProvider() })), {}, logger).loadIdentityPlanAtStartup();

    expect(logger.lines.some((line) => line.startsWith('log identity_plan_loaded '))).toBe(true);
  });

  it('falls back to the baked path when nothing is bundled', () => {
    const baked = writePlan(plan({ [PROVIDER]: jwtProvider() }));
    const core = createIdentityCore<IdentityProfileDocument>({
      reasons: REASONS,
      planSchemaVersion: SCHEMA_VERSION,
      bundledPlanPath: path.join(planDir, 'absent.json'),
      bakedPlanPath: baked,
      lateBoundSetting: () => null,
      logger: new RecordingLogger(),
    });

    expect(() => core.loadIdentityPlanAtStartup()).not.toThrow();
  });

  it('refuses to start when no plan is bundled and none is baked', () => {
    const core = coreFor(path.join(planDir, 'absent.json'));

    expect(() => core.loadIdentityPlanAtStartup()).toThrow('Identity provider plan not found');
  });

  it('refuses a plan written for another schema version', () => {
    const core = coreFor(writePlan(plan({ [PROVIDER]: jwtProvider() }, SCHEMA_VERSION + 1)));

    expect(() => core.loadIdentityPlanAtStartup()).toThrow(`schema version ${SCHEMA_VERSION + 1} is not supported`);
  });

  it('refuses a plan that is not JSON', () => {
    const planPath = path.join(planDir, 'broken.json');
    fs.writeFileSync(planPath, '{', 'utf-8');

    expect(() => coreFor(planPath).loadIdentityPlanAtStartup()).toThrow('Failed to parse identity provider plan JSON');
  });

  it('refuses a provider of an unknown credential kind', () => {
    const core = coreFor(writePlan(plan({ [PROVIDER]: jwtProvider({ credential: 'saml' }) })));

    expect(() => core.loadIdentityPlanAtStartup()).toThrow("has credential kind 'saml'");
  });

  it.each([
    ['a negative key-set lifetime', { jwksCacheTtlSeconds: -1 }, 'jwksCacheTtlSeconds'],
    ['a key endpoint with credentials', { jwksFetch: { url: 'https://user:pw@keys.example.test/' } }, 'jwksFetch.url'],
    ['a key endpoint of another scheme', { jwksFetch: { url: 'file:///etc/keys' } }, 'jwksFetch.url'],
    ['a Host header that is not a bare host', { jwksFetch: { url: 'https://keys.example.test/', hostHeader: 'a b' } }, 'hostHeader'],
  ])('refuses %s without echoing the value', (_case, overrides, member) => {
    const core = coreFor(writePlan(plan({ [PROVIDER]: jwtProvider(overrides) })));

    expect(() => core.loadIdentityPlanAtStartup()).toThrow(member);
    expect(() => core.loadIdentityPlanAtStartup()).not.toThrow('pw@');
  });

  it('reports a provider revocation policy and an enabled profile projection', () => {
    const projection = { enabled: true, profileStore: 'main', linkKey: ['sub'], fields: {} };
    const core = providerCore(jwtProvider({ profileProjection: projection }));

    expect(core.providerRevocationPolicy(PROVIDER)).toEqual({ mode: 'none', tokenIdClaim: 'jti' });
    expect(core.providerProfileProjection(PROVIDER)).toEqual(projection);
    expect(core.providerRevocationPolicy('unknown')).toBeUndefined();
  });

  it('reports no projection for a disabled one', () => {
    const projection = { enabled: false, profileStore: 'main', linkKey: ['sub'], fields: {} };

    expect(providerCore(jwtProvider({ profileProjection: projection })).providerProfileProjection(PROVIDER)).toBeUndefined();
  });
});
