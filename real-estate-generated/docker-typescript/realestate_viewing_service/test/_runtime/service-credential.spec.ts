/**
 * Jest spec of the service credential runtime module (`src/_runtime/service-credential.ts`).
 *
 * The bounded acquisition runs real minters: one that answers, one that refuses and one that
 * never answers. The role-session and managed-identity minters run over in-memory providers of
 * the shapes the platform SDKs return. The client-credentials minter reads a real credentials
 * file and calls a real token endpoint on the loopback interface. Every refusal path of today's
 * credential module is exercised and keeps its message.
 *
 * Shipped by cruftfree-codegen-typescript-core and emitted verbatim. Do not edit manually.
 */
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { createServer } from 'node:http';
import type { IncomingMessage, Server, ServerResponse } from 'node:http';
import type { AddressInfo } from 'node:net';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import {
  createClientCredentialsTokens,
  createServiceCredential,
  managedIdentityMinter,
  roleSessionMinter,
} from '../../src/_runtime/service-credential';
import type { AccessTokenCredential, MachineCredentials } from '../../src/_runtime/service-credential';

const TIMEOUT_ERROR_NAME = 'ServiceCredentialTimeoutError';
const ACQUIRE_TIMEOUT_MS = 50;
const CREDENTIAL = 'machine-credential';
const AUDIENCE_SETTING = 'IDENTITY_MACHINE_AUDIENCE';
const MACHINE_AUDIENCE = '00000000-0000-0000-0000-000000000001';
const MANAGEMENT_AUDIENCE = 'urn:identity:management';
const SKEW_SECONDS = 30;
const LIFETIME_SECONDS = 3600;
const MILLISECONDS_PER_SECOND = 1000;

describe('bounded acquisition', () => {
  function credentialMintedBy(mint: () => Promise<string>) {
    return createServiceCredential({ mint, acquireTimeoutMs: ACQUIRE_TIMEOUT_MS, timeoutErrorName: TIMEOUT_ERROR_NAME });
  }

  it('returns the minted credential', async () => {
    const { acquireServiceCredential } = credentialMintedBy(async () => CREDENTIAL);

    expect(await acquireServiceCredential()).toBe(CREDENTIAL);
  });

  it('propagates a mint failure unchanged', async () => {
    const { acquireServiceCredential } = credentialMintedBy(async () => {
      throw new Error('platform credential endpoint refused');
    });

    await expect(acquireServiceCredential()).rejects.toThrow('platform credential endpoint refused');
  });

  it('refuses past the bound with the named timeout error', async () => {
    const { acquireServiceCredential, TimeoutError } = credentialMintedBy(() => new Promise<string>(() => undefined));

    const refusal = acquireServiceCredential();

    await expect(refusal).rejects.toBeInstanceOf(TimeoutError);
    const error = (await refusal.catch((caught: unknown) => caught)) as Error;
    expect(error.name).toBe(TIMEOUT_ERROR_NAME);
    expect(error.message).toContain(`within ${ACQUIRE_TIMEOUT_MS}ms`);
  });
});

describe('role session minter', () => {
  it('mints the session token from a fresh provider per mint', async () => {
    let providers = 0;
    const mint = roleSessionMinter(() => {
      providers += 1;
      return async () => ({ sessionToken: CREDENTIAL });
    });

    expect(await mint()).toBe(CREDENTIAL);
    expect(await mint()).toBe(CREDENTIAL);
    expect(providers).toBe(2);
  });

  it('refuses role credentials without a session token', async () => {
    const mint = roleSessionMinter(() => async () => ({}));

    await expect(mint()).rejects.toThrow('No AWS role credentials available for service-to-service auth.');
  });
});

describe('managed identity minter', () => {
  class RecordingCredential implements AccessTokenCredential {
    readonly scopes: string[] = [];

    constructor(private readonly answer: { readonly token: string } | null) {}

    async getToken(scope: string): Promise<{ readonly token: string } | null> {
      this.scopes.push(scope);
      return this.answer;
    }
  }

  it("mints for the machine identity provider's audience", async () => {
    const credential = new RecordingCredential({ token: CREDENTIAL });
    const mint = managedIdentityMinter({
      credential: () => credential,
      audienceSetting: AUDIENCE_SETTING,
      readAudience: () => MACHINE_AUDIENCE,
    });

    expect(await mint()).toBe(CREDENTIAL);
    expect(credential.scopes).toEqual([`${MACHINE_AUDIENCE}/.default`]);
  });

  it.each([
    ['unset', null],
    ['empty', ''],
  ])('refuses an %s audience setting naming the setting', async (_case, audience) => {
    const credential = new RecordingCredential({ token: CREDENTIAL });
    const mint = managedIdentityMinter({
      credential: () => credential,
      audienceSetting: AUDIENCE_SETTING,
      readAudience: () => audience,
    });

    await expect(mint()).rejects.toThrow(`Machine-identity audience setting '${AUDIENCE_SETTING}' is not set.`);
    expect(credential.scopes).toEqual([]);
  });

  it('refuses when the credential returns no token', async () => {
    const mint = managedIdentityMinter({
      credential: () => new RecordingCredential(null),
      audienceSetting: AUDIENCE_SETTING,
      readAudience: () => MACHINE_AUDIENCE,
    });

    await expect(mint()).rejects.toThrow('Failed to acquire managed-identity token.');
  });
});

interface TokenRequest {
  readonly authorization: string | undefined;
  readonly host: string | undefined;
  readonly form: URLSearchParams;
}

/** A loopback token endpoint answering each request with the next queued reply. */
class TokenEndpoint {
  readonly requests: TokenRequest[] = [];
  reply: { readonly status: number; readonly body: unknown } = { status: 200, body: {} };
  private readonly server: Server = createServer((req, res) => this.handle(req, res));

  async start(): Promise<string> {
    await new Promise<void>((resolve) => this.server.listen(0, '127.0.0.1', resolve));
    return `http://127.0.0.1:${(this.server.address() as AddressInfo).port}/oauth/v2/token`;
  }

  async stop(): Promise<void> {
    await new Promise<void>((resolve) => this.server.close(() => resolve()));
  }

  private handle(req: IncomingMessage, res: ServerResponse): void {
    const chunks: Buffer[] = [];
    req.on('data', (chunk: Buffer) => chunks.push(chunk));
    req.on('end', () => {
      this.requests.push({ authorization: req.headers.authorization, host: req.headers.host, form: new URLSearchParams(Buffer.concat(chunks).toString('utf-8')) });
      res.writeHead(this.reply.status, { 'Content-Type': 'application/json' });
      res.end(typeof this.reply.body === 'string' ? this.reply.body : JSON.stringify(this.reply.body));
    });
  }
}

/** An unsigned JWT whose `exp` is `expiresAt` (epoch seconds). */
function tokenExpiringAt(expiresAt: number): string {
  const encode = (value: object): string => Buffer.from(JSON.stringify(value)).toString('base64url');
  return `${encode({ alg: 'none' })}.${encode({ exp: expiresAt })}.signature`;
}

describe('client credentials minter', () => {
  const endpoint = new TokenEndpoint();
  let directory: string;
  let credentials: MachineCredentials;

  function writeCredentials(name: string, content: object): string {
    const file = join(directory, name);
    writeFileSync(file, JSON.stringify(content), 'utf-8');
    return file;
  }

  function tokensReading(file: string) {
    return createClientCredentialsTokens({ credentialsFile: file, tokenExpirySkewSeconds: SKEW_SECONDS });
  }

  beforeAll(async () => {
    directory = mkdtempSync(join(tmpdir(), 'service-credential-spec-'));
    credentials = {
      clientId: 'machine-client',
      clientSecret: 'machine-client-secret',
      tokenUrl: await endpoint.start(),
      hostHeader: 'identity.internal',
      audience: 'machine-project',
      instanceOrigin: 'http://identity.internal',
    };
  });

  afterAll(async () => {
    await endpoint.stop();
    rmSync(directory, { recursive: true, force: true });
  });

  beforeEach(() => {
    endpoint.requests.length = 0;
  });

  it('loads every field of the credentials file', () => {
    expect(tokensReading(writeCredentials('complete.json', credentials)).loadMachineCredentials()).toEqual(credentials);
  });

  describe('the organization holding a provider\'s users', () => {
    it('names the organization of a provider that has one of its own', () => {
      const file = writeCredentials('organizations.json', { ...credentials, organizations: { buyers: 'org-1' } });

      expect(tokensReading(file).providerOrganization('buyers')).toBe('org-1');
    });

    it.each([
      ['a provider without one', { organizations: { buyers: 'org-1' } }, 'staff'],
      ['a file with no organizations member', {}, 'buyers'],
      ['a name that only the object prototype defines', { organizations: { buyers: 'org-1' } }, 'constructor'],
    ])('names none for %s', (_case, extra, provider) => {
      const file = writeCredentials('no-organization.json', { ...credentials, ...extra });

      expect(tokensReading(file).providerOrganization(provider)).toBeUndefined();
    });

    it.each([
      ['not an object', 'org-1'],
      ['an array', ['org-1']],
      ['holding a blank id', { buyers: '' }],
      ['holding an id that is not a string', { buyers: 7 }],
    ])('refuses an organizations member that is %s', (_case, organizations) => {
      const file = writeCredentials('bad-organizations.json', { ...credentials, organizations });

      expect(() => tokensReading(file).providerOrganization('buyers')).toThrow(
        "holds an 'organizations' member that is not an object of organization ids",
      );
    });
  });

  it('refuses an unreadable credentials file naming the file', () => {
    const missing = join(directory, 'absent.json');

    expect(() => tokensReading(missing).loadMachineCredentials()).toThrow(
      `Machine credentials file '${missing}' could not be read`,
    );
  });

  it.each(['clientId', 'clientSecret', 'tokenUrl', 'hostHeader', 'audience', 'instanceOrigin'])(
    'refuses a credentials file without %s',
    (field) => {
      const file = writeCredentials(`without-${field}.json`, { ...credentials, [field]: '' });

      expect(() => tokensReading(file).loadMachineCredentials()).toThrow(
        'is missing clientId/clientSecret/tokenUrl/hostHeader/audience/instanceOrigin.',
      );
    },
  );

  it('mints for the machine-project audience with the client credentials, then serves the cache', async () => {
    const token = tokenExpiringAt(Math.floor(Date.now() / MILLISECONDS_PER_SECOND) + LIFETIME_SECONDS);
    endpoint.reply = { status: 200, body: { access_token: token } };
    const tokens = tokensReading(writeCredentials('mint.json', credentials));

    expect(await tokens.mintServiceCredential()).toBe(token);
    expect(await tokens.mintServiceCredential()).toBe(token);
    expect(endpoint.requests).toHaveLength(1);
    const [request] = endpoint.requests;
    const basic = Buffer.from(`${credentials.clientId}:${credentials.clientSecret}`).toString('base64');
    expect(request.authorization).toBe(`Basic ${basic}`);
    // The instance is addressed by the Host header the credentials file names, not the address reached.
    expect(request.host).toBe(credentials.hostHeader);
    expect(request.form.get('grant_type')).toBe('client_credentials');
    expect(request.form.get('scope')).toBe(`openid ${credentials.audience}`);
  });

  it('renews a token inside the expiry skew', async () => {
    const token = tokenExpiringAt(Math.floor(Date.now() / MILLISECONDS_PER_SECOND) + SKEW_SECONDS - 1);
    endpoint.reply = { status: 200, body: { access_token: token } };
    const tokens = tokensReading(writeCredentials('renew.json', credentials));

    await tokens.mintServiceCredential();
    await tokens.mintServiceCredential();

    expect(endpoint.requests).toHaveLength(2);
  });

  it("caches a management-API token under that API's own audience", async () => {
    const token = tokenExpiringAt(Math.floor(Date.now() / MILLISECONDS_PER_SECOND) + LIFETIME_SECONDS);
    endpoint.reply = { status: 200, body: { access_token: token } };
    const tokens = tokensReading(writeCredentials('management.json', credentials));

    await tokens.mintServiceCredential();
    await tokens.acquireProviderMetadataCredential(MANAGEMENT_AUDIENCE);

    expect(endpoint.requests.map((request) => request.form.get('scope'))).toEqual([
      `openid ${credentials.audience}`,
      `openid ${MANAGEMENT_AUDIENCE}`,
    ]);
  });

  it('refuses a token endpoint answering other than 200, with its status', async () => {
    endpoint.reply = { status: 401, body: 'invalid_client' };
    const tokens = tokensReading(writeCredentials('refused.json', credentials));

    await expect(tokens.mintServiceCredential()).rejects.toThrow(
      'Failed to acquire Zitadel machine token via client_credentials (HTTP 401): invalid_client.',
    );
  });

  it('refuses a token response without an access token', async () => {
    endpoint.reply = { status: 200, body: { token_type: 'Bearer' } };
    const tokens = tokensReading(writeCredentials('no-token.json', credentials));

    await expect(tokens.mintServiceCredential()).rejects.toThrow("Zitadel token response did not contain an 'access_token'.");
  });
});
