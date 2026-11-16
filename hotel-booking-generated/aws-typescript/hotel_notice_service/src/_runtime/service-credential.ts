/**
 * Service credential core -- the platform machine-identity credential an outbound call presents.
 *
 * The credential is the platform-managed machine identity, never a locally signed
 * application token. Acquiring it is bounded on its own: never charged against an
 * outbound call's timeout, and never left unbounded. Past the bound the acquisition
 * raises the error the shared vocabulary names, so a caller tells "this service could
 * not obtain its credential" apart from "the dependency timed out".
 *
 * One minter per platform strategy obtains the credential:
 *   role session (`roleSessionMinter`): the session token of the role's temporary
 *     credentials, from the provider chain the binding passes;
 *   managed identity (`managedIdentityMinter`): a token from the credential the binding
 *     passes, minted for the machine identity provider's audience setting;
 *   client credentials (`createClientCredentialsTokens`): a client_credentials grant with
 *     the machine credentials file the identity provisioning job writes, cached per
 *     audience until shortly before expiry.
 *
 * Every SDK object, setting reader, file path, bound and error name is a parameter the
 * service's `discovery/service-credential.ts` binding passes, so this module imports no
 * platform SDK and reads no environment.
 *
 * Shipped by cruftfree-codegen-typescript-core and emitted verbatim. Do not edit manually.
 */
import { readFileSync } from 'node:fs';
import * as http from 'node:http';
import * as https from 'node:https';
import { Logger } from '@nestjs/common';

/** Obtains the credential from the platform; `acquireServiceCredential` bounds it. */
export type ServiceCredentialMinter = () => Promise<string>;

/** Everything project-specific the bounded acquisition needs, passed by the service's binding. */
export interface ServiceCredentialOptions {
  readonly mint: ServiceCredentialMinter;
  /** The longest acquiring the credential may take. */
  readonly acquireTimeoutMs: number;
  /** The `name` of the error raised past the bound (the shared vocabulary's). */
  readonly timeoutErrorName: string;
}

/** The error class raised when the credential was not obtained within its bound. */
export type ServiceCredentialTimeoutErrorClass = new (message: string) => Error;

/** What a service's binding exports. */
export interface ServiceCredential {
  /** Return the managed machine-identity credential for an outbound call, within its bound. */
  readonly acquireServiceCredential: () => Promise<string>;
  readonly TimeoutError: ServiceCredentialTimeoutErrorClass;
}

/** The bounded acquisition of one service's machine-identity credential. */
export function createServiceCredential(options: ServiceCredentialOptions): ServiceCredential {
  const credentialLogger = new Logger('ServiceCredential');

  /**
   * The machine-identity credential was not obtained within its bound. Thrown instead
   * of a timeout of the call the credential was for.
   */
  class ServiceCredentialTimeoutError extends Error {
    constructor(message: string) {
      super(message);
      this.name = options.timeoutErrorName;
    }
  }

  async function acquireServiceCredential(): Promise<string> {
    let timedOut = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const deadline = new Promise<never>((_resolve, reject) => {
      timer = setTimeout(() => {
        timedOut = true;
        reject(
          new ServiceCredentialTimeoutError(
            `The machine-identity credential was not obtained within ${options.acquireTimeoutMs}ms. ` +
              'Expected the platform credential endpoint to answer; check its reachability from this service.',
          ),
        );
      }, options.acquireTimeoutMs);
    });
    const minting = options.mint();
    // A mint that fails after the bound already failed the call: it is recorded, never
    // left as an unhandled rejection.
    minting.catch((err: unknown) => {
      if (timedOut) {
        credentialLogger.warn(
          `service_credential_failed_after_bound error_type=${err instanceof Error ? err.name : typeof err}`,
        );
      }
    });
    try {
      return await Promise.race([minting, deadline]);
    } finally {
      clearTimeout(timer);
    }
  }

  return { acquireServiceCredential, TimeoutError: ServiceCredentialTimeoutError };
}

/** A role credential provider: resolves the role's temporary credentials. */
export type RoleCredentialProvider = () => Promise<{ readonly sessionToken?: string }>;

/** Mints the role session token from a fresh provider of `providerChain` per mint. */
export function roleSessionMinter(providerChain: () => RoleCredentialProvider): ServiceCredentialMinter {
  return async (): Promise<string> => {
    const credentials = await providerChain()();
    if (!credentials.sessionToken) {
      throw new Error('No AWS role credentials available for service-to-service auth.');
    }
    return credentials.sessionToken;
  };
}

/** A credential that mints an access token for one scope (`null` when it cannot). */
export interface AccessTokenCredential {
  getToken(scope: string): Promise<{ readonly token: string } | null>;
}

/** What the managed-identity minter needs, passed by the service's binding. */
export interface ManagedIdentityMinterOptions {
  /** The service's managed-identity credential, built per mint. */
  readonly credential: () => AccessTokenCredential;
  /** The deploy-time setting carrying the machine identity provider's audience. */
  readonly audienceSetting: string;
  /** Reads that setting; `null` (or empty) when it is not set. */
  readonly readAudience: () => string | null;
}

const MANAGED_IDENTITY_SCOPE_SUFFIX = '/.default';

/**
 * Mints a managed-identity token for the machine identity provider's audience -- its client-ID
 * GUID, never the callee's network address, which is not a registered OAuth resource.
 */
export function managedIdentityMinter(options: ManagedIdentityMinterOptions): ServiceCredentialMinter {
  function resolveMachineAudience(): string {
    const value = options.readAudience();
    if (!value) {
      throw new Error(
        `Machine-identity audience setting '${options.audienceSetting}' is not set. ` +
          'It carries the machine identity provider\'s Entra client-ID GUID (a deploy-time app ' +
          'setting); the service-to-service credential is minted for this resource. Ensure the ' +
          'identity audience app settings are wired by the platform deployer.',
      );
    }
    return value;
  }

  return async (): Promise<string> => {
    const token = await options.credential().getToken(`${resolveMachineAudience()}${MANAGED_IDENTITY_SCOPE_SUFFIX}`);
    if (!token) {
      throw new Error('Failed to acquire managed-identity token.');
    }
    return token.token;
  };
}

/** The machine service-account credentials the identity provisioning job writes. */
export interface MachineCredentials {
  clientId: string;
  clientSecret: string;
  // The token endpoint and the `Host` header it must be addressed with. A provider
  // management-API write targets the same identity instance and presents the same `Host` header.
  tokenUrl: string;
  hostHeader: string;
  audience: string;
  // The identity instance base URL, doubling as the management-API base. Unused by the
  // service credential itself; read by the identity write-back client.
  instanceOrigin: string;
}

/** What the client-credentials minter needs, passed by the service's binding. */
export interface ClientCredentialsOptions {
  /** The machine credentials file, on the shared volume mounted read-only into the service. */
  readonly credentialsFile: string;
  /** Renew a cached token this many seconds before its real expiry. */
  readonly tokenExpirySkewSeconds: number;
}

/** What a client-credentials binding exports. */
export interface ClientCredentialsTokens {
  readonly loadMachineCredentials: () => MachineCredentials;
  /**
   * The id of the organization holding a provider's users when the provider has one of its own
   * (a provider that requires a second factor at sign-in), else `undefined`: the users of every
   * other provider live in the instance's default organization, which no call needs to name.
   *
   * @throws Error when the credentials file cannot be read or its `organizations` member is malformed.
   */
  readonly providerOrganization: (provider: string) => string | undefined;
  /** The machine token for the machine-project audience the credentials file names. */
  readonly mintServiceCredential: ServiceCredentialMinter;
  /**
   * A machine token scoped to a provider management-API's own audience: that API gates on a
   * DIFFERENT `aud` than sibling services do, so the identity write-back client mints for it.
   */
  readonly acquireProviderMetadataCredential: (audience: string) => Promise<string>;
}

/** One finished HTTP answer: the status and the whole body as text. */
export interface InstanceAnswer {
  readonly status: number;
  readonly text: string;
}

/** The longest answer an identity instance is read for; past it the request is destroyed. */
const MAX_ANSWER_BYTES = 1048576;

/**
 * One HTTP request to the identity instance, presenting the request's own `Host` header.
 *
 * The identity server picks its instance by `Host`, and the credentials file names the header
 * the instance answers to (`hostHeader`) apart from the address the service reaches it at.
 * Node's global `fetch` discards a `Host` header the caller sets, so the request would reach the
 * instance under its network name and be refused ("Instance not found"); `node:http(s)` sends it.
 *
 * @throws Error on a transport failure, a timeout, or an answer over `MAX_ANSWER_BYTES`.
 */
export function sendToInstance(
  method: string,
  url: string,
  headers: Readonly<Record<string, string>>,
  body: string | undefined,
  timeoutMs: number,
): Promise<InstanceAnswer> {
  const target = new URL(url);
  const transport = target.protocol === 'https:' ? https : http;
  const sent: Record<string, string | number> = { ...headers };
  if (body !== undefined) {
    sent['Content-Length'] = Buffer.byteLength(body);
  }
  return new Promise<InstanceAnswer>((resolve, reject) => {
    const request = transport.request(target, { method, headers: sent, timeout: timeoutMs }, (response) => {
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
    });
    request.on('timeout', () => request.destroy(new Error('the request timed out')));
    request.on('error', reject);
    request.end(body);
  });
}

/** Optional member of the credentials file: provider name -> the id of the organization holding its users. */
const ORGANIZATIONS_MEMBER = 'organizations';
const HTTP_OK = 200;
const MILLISECONDS_PER_SECOND = 1000;
/** Acquiring a machine token is bounded on its own, apart from the call it is for. */
const TOKEN_REQUEST_TIMEOUT_MS = 10000;
const JWT_SEGMENT_COUNT = 3;
const ERROR_BODY_PREVIEW_CHARS = 300;

/** The `exp` claim of a JWT, or `0` when the token is not a readable JWT. */
function decodeTokenExpiry(token: string): number {
  const parts = token.split('.');
  if (parts.length !== JWT_SEGMENT_COUNT) {
    return 0;
  }
  try {
    const payload = JSON.parse(Buffer.from(parts[1], 'base64url').toString('utf-8'));
    const exp = (payload as Record<string, unknown>).exp;
    return typeof exp === 'number' ? exp : 0;
  } catch {
    return 0;
  }
}

/** Client-credentials machine tokens read from the machine credentials file. */
export function createClientCredentialsTokens(options: ClientCredentialsOptions): ClientCredentialsTokens {
  // Machine tokens cached by the audience they were minted for: inter-service calls use the
  // machine-project audience in the credentials file (the empty-string key), a provider
  // management-API write that API's own audience, so one never masks the other.
  const cachedTokens = new Map<string, { token: string; expiry: number }>();

  function readDocument(): Record<string, unknown> {
    let raw: unknown;
    try {
      raw = JSON.parse(readFileSync(options.credentialsFile, 'utf-8'));
    } catch (err) {
      throw new Error(
        `Machine credentials file '${options.credentialsFile}' could not be read: ${String(err)}. ` +
          'Ensure this service depends on the Zitadel init-job and mounts the shared volume.',
      );
    }
    return raw as Record<string, unknown>;
  }

  function providerOrganization(provider: string): string | undefined {
    const organizations = readDocument()[ORGANIZATIONS_MEMBER];
    if (organizations === undefined) {
      return undefined;
    }
    if (
      organizations === null ||
      typeof organizations !== 'object' ||
      Array.isArray(organizations) ||
      !Object.values(organizations).every((id) => typeof id === 'string' && id !== '')
    ) {
      throw new Error(
        `Machine credentials file '${options.credentialsFile}' holds an '${ORGANIZATIONS_MEMBER}' member ` +
          'that is not an object of organization ids. Regenerate and redeploy so the init-job rewrites the file.',
      );
    }
    return Object.prototype.hasOwnProperty.call(organizations, provider)
      ? (organizations as Record<string, string>)[provider]
      : undefined;
  }

  function loadMachineCredentials(): MachineCredentials {
    const data = readDocument();
    const { clientId, clientSecret, tokenUrl, hostHeader, audience, instanceOrigin } = data;
    if (
      typeof clientId !== 'string' ||
      !clientId ||
      typeof clientSecret !== 'string' ||
      !clientSecret ||
      typeof tokenUrl !== 'string' ||
      !tokenUrl ||
      typeof hostHeader !== 'string' ||
      !hostHeader ||
      typeof audience !== 'string' ||
      !audience ||
      typeof instanceOrigin !== 'string' ||
      !instanceOrigin
    ) {
      throw new Error(
        `Machine credentials file '${options.credentialsFile}' is missing ` +
          'clientId/clientSecret/tokenUrl/hostHeader/audience/instanceOrigin.',
      );
    }
    return { clientId, clientSecret, tokenUrl, hostHeader, audience, instanceOrigin };
  }

  async function acquireMachineToken(scopeAudience: string): Promise<string> {
    const now = Date.now() / MILLISECONDS_PER_SECOND;
    const cached = cachedTokens.get(scopeAudience);
    if (cached && now < cached.expiry - options.tokenExpirySkewSeconds) {
      return cached.token;
    }
    const creds = loadMachineCredentials();
    const audience = scopeAudience || creds.audience;
    const body = new URLSearchParams({
      grant_type: 'client_credentials',
      scope: `openid ${audience}`,
    });
    const basic = Buffer.from(`${creds.clientId}:${creds.clientSecret}`).toString('base64');
    const response = await sendToInstance(
      'POST',
      creds.tokenUrl,
      {
        Authorization: `Basic ${basic}`,
        'Content-Type': 'application/x-www-form-urlencoded',
        Host: creds.hostHeader,
      },
      body.toString(),
      TOKEN_REQUEST_TIMEOUT_MS,
    );
    if (response.status !== HTTP_OK) {
      throw new Error(
        `Failed to acquire Zitadel machine token via client_credentials (HTTP ${response.status}): ` +
          `${response.text.slice(0, ERROR_BODY_PREVIEW_CHARS)}.`,
      );
    }
    const payload = JSON.parse(response.text) as Record<string, unknown>;
    const token = payload.access_token;
    if (typeof token !== 'string' || !token) {
      throw new Error("Zitadel token response did not contain an 'access_token'.");
    }
    const expiresIn = typeof payload.expires_in === 'number' ? payload.expires_in : 0;
    const expiry = decodeTokenExpiry(token) || Date.now() / MILLISECONDS_PER_SECOND + expiresIn;
    cachedTokens.set(scopeAudience, { token, expiry });
    return token;
  }

  return {
    loadMachineCredentials,
    providerOrganization,
    // The machine-project audience in the credentials file authenticates to every peer.
    mintServiceCredential: () => acquireMachineToken(''),
    acquireProviderMetadataCredential: (audience: string) => acquireMachineToken(audience),
  };
}
