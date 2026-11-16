/**
 * Microservice helper functions for generated TypeScript code.
 *
 * Uses axios for HTTP calls and opossum circuit breakers for resilience.
 * Peer base URLs come from the `<peer>_base_url` keys of the assembled settings (one per declared
 * dependency, resolved when used); a peer may also be registered at runtime. No environment
 * variable is read. Every peer call presents this service's platform-managed machine credential.
 */
import axios, { type AxiosRequestConfig, type AxiosResponse } from 'axios';
import CircuitBreaker from 'opossum';
import { getSettings } from "../config/settings";
import { acquireServiceCredential } from "../discovery/service-credential";
import { DeadlineExceededError, runWithDeadline } from "../interceptors/timeout.interceptor";
import { wireJsonReplacer } from '../common/wire-json';

// ── Service identity ────────────────────────────────────────────────────────

/**
 * The headers of a peer call: this service's machine credential as a bearer token, then the
 * caller's own headers. A credential that cannot be acquired fails the call -- an
 * unauthenticated peer call is never sent.
 */
async function _peerHeaders(headers?: Record<string, string>): Promise<Record<string, string>> {
  const credential = await acquireServiceCredential();
  return { Authorization: `Bearer ${credential}`, ...(headers ?? {}) };
}

/** The content type of a peer call's body, which this module writes itself: axios's own JSON writer takes no replacer. */
const _JSON_BODY_HEADERS: Readonly<Record<string, string>> = { 'Content-Type': 'application/json' };

// ── Service URL resolution ──────────────────────────────────────────────────

/** The base URL of each declared dependency, under every name the dependency is addressed by. */
const _PEER_URLS: Readonly<Record<string, () => string>> = {
  "listing-service": () => getSettings().connections.realestate_listing_service_base_url,
  "realestate-listing-service": () => getSettings().connections.realestate_listing_service_base_url,
};

/** One name per declared dependency: the one `listServices` reports it under. */
const _DECLARED_PEERS: readonly string[] = [
  "realestate-listing-service",
];

/** Peers registered at runtime; they take precedence over the declared dependencies. */
const _registeredUrls = new Map<string, string>();

function _normalizeServiceName(service: string): string {
  return service.trim().toLowerCase().replace(/_/g, '-');
}

export function _msGetServiceUrl(service: string): string {
  const name = _normalizeServiceName(service);
  const registered = _registeredUrls.get(name);
  if (registered !== undefined) {
    return registered;
  }
  const declared = _PEER_URLS[name];
  if (declared === undefined) {
    throw new Error(
      `Service URL for "${service}" not configured: it is neither a declared dependency nor ` +
        `registered. Known: ${_knownServices().join(', ') || '(none)'}.`,
    );
  }
  const url = declared();
  if (url === '') {
    throw new Error(`Service URL for "${service}" is empty in the assembled settings.`);
  }
  return url;
}

/** Every declared dependency (one name each) and every runtime-registered peer, sorted. */
function _knownServices(): string[] {
  return [...new Set([..._DECLARED_PEERS, ..._registeredUrls.keys()])].sort();
}

// ── HTTP calls ──────────────────────────────────────────────────────────────

/**
 * A call to a peer service failed: names the peer, the route and the status. Never the resolved
 * URL, host or port: the axios error, whose message and `config` carry the address, is neither
 * attached nor logged. `status` is undefined when the peer gave no response (a refused
 * connection, a timeout).
 */
export class PeerCallError extends Error {
  readonly service: string;
  readonly route: string;
  readonly status: number | undefined;

  constructor(service: string, route: string, status: number | undefined) {
    const outcome = status === undefined ? 'no response' : `status ${status}`;
    super(`Call to service '${service}' route '${route}' failed: ${outcome}.`);
    this.name = 'PeerCallError';
    this.service = service;
    this.route = route;
    this.status = status;
  }
}

/** An error's class name -- never its text, which can carry an internal address. */
function _errorName(error: unknown): string {
  return error instanceof Error ? error.name : typeof error;
}

/** The `PeerCallError` a failed peer request raises, logged by the peer, the route and the status. */
function _peerCallError(service: string, route: string, error: unknown): PeerCallError {
  const status = axios.isAxiosError(error) ? error.response?.status : undefined;
  console.error(
    `inter_service_http_failed service=${service} route=${route} status=${status ?? 'none'} error=${_errorName(error)}`,
  );
  return new PeerCallError(service, route, status);
}

/**
 * `Microservice.call(service, endpoint, params?)`: POST the JSON `params` (an empty
 * object when absent) to `<service base URL>/<endpoint>` and return the response body.
 * A non-2xx status, or no response, raises `PeerCallError`.
 */
export async function _msCall(
  service: string,
  endpoint: string,
  params?: Record<string, unknown>,
): Promise<unknown> {
  const baseUrl = _msGetServiceUrl(service);
  const headers = await _peerHeaders(_JSON_BODY_HEADERS);
  try {
    const response = await axios.post(`${baseUrl}/${endpoint}`, JSON.stringify(params ?? {}, wireJsonReplacer), { headers });
    return response.data;
  } catch (error: unknown) {
    throw _peerCallError(service, `/${endpoint}`, error);
  }
}

/**
 * `Microservice.callAsync(service, endpoint, params?)`: `_msCall`, not awaited. No caller is
 * waiting to see a failure, so it is logged here -- the peer, the endpoint and the error's
 * name, never its text, which carries the peer's internal address.
 */
export function _msCallAsync(
  service: string,
  endpoint: string,
  params?: Record<string, unknown>,
): void {
  _msCall(service, endpoint, params).catch((error: unknown) => {
    console.warn(`call_async_failed service=${service} endpoint=${endpoint} error=${_errorName(error)}`);
  });
}

export async function _msPost(service: string, path: string, body: unknown): Promise<unknown> {
  const baseUrl = _msGetServiceUrl(service);
  const headers = await _peerHeaders(_JSON_BODY_HEADERS);
  try {
    const response = await axios.post(`${baseUrl}${path}`, JSON.stringify(body, wireJsonReplacer), { headers });
    return response.data;
  } catch (error: unknown) {
    throw _peerCallError(service, path, error);
  }
}

export async function _msPut(service: string, path: string, body: unknown): Promise<unknown> {
  const baseUrl = _msGetServiceUrl(service);
  const headers = await _peerHeaders(_JSON_BODY_HEADERS);
  try {
    const response = await axios.put(`${baseUrl}${path}`, JSON.stringify(body, wireJsonReplacer), { headers });
    return response.data;
  } catch (error: unknown) {
    throw _peerCallError(service, path, error);
  }
}

export async function _msDelete(service: string, path: string): Promise<unknown> {
  const baseUrl = _msGetServiceUrl(service);
  const headers = await _peerHeaders();
  try {
    const response = await axios.delete(`${baseUrl}${path}`, { headers });
    return response.data;
  } catch (error: unknown) {
    throw _peerCallError(service, path, error);
  }
}

/** The option keys `Microservice.callWithOptions` applies; any other key is an error. */
const _MS_CALL_OPTION_KEYS: ReadonlySet<string> = new Set(['method', 'headers', 'timeout']);

/**
 * `Microservice.callWithOptions(service, endpoint, options)`: request
 * `<service base URL><endpoint>` with `options.method` (default `GET`),
 * `options.headers` and `options.timeout` (seconds). A non-2xx status raises.
 */
export async function _msCallWithOptions(
  service: string,
  endpoint: string,
  options: { method?: string; headers?: Record<string, string>; timeout?: number },
): Promise<unknown> {
  const unknown = Object.keys(options).filter((key) => !_MS_CALL_OPTION_KEYS.has(key));
  if (unknown.length > 0) {
    throw new Error(
      `Unknown Microservice.callWithOptions option(s) ${unknown.join(', ')}; ` +
        `supported: ${[..._MS_CALL_OPTION_KEYS].join(', ')}.`,
    );
  }
  const baseUrl = _msGetServiceUrl(service);
  const headers = await _peerHeaders(options.headers);
  try {
    const response = await axios.request({
      method: (options.method ?? 'GET') as AxiosRequestConfig['method'],
      url: `${baseUrl}${endpoint}`,
      headers,
      timeout: options.timeout === undefined ? undefined : options.timeout * 1000,
    });
    return response.data;
  } catch (error: unknown) {
    throw _peerCallError(service, endpoint, error);
  }
}

/**
 * A POST with explicit headers got no response: never the URL or those headers. A status
 * is an answer, returned to the caller; an axios error's `config` holds the signature.
 */
export class HttpPostError extends Error {
  override readonly name = 'HttpPostError';
}

/** POST a UTF-8 string body with explicit headers (e.g. webhooks with HMAC). */
export async function _httpPostWithHeaders(
  url: string,
  body: string,
  headers: Record<string, string>,
): Promise<{ statusCode: number; body: unknown }> {
  let response: AxiosResponse;
  try {
    response = await axios.post(url, body, {
      headers,
      validateStatus: () => true,
    });
  } catch (error: unknown) {
    console.error(`http_post_unreachable error=${_errorName(error)}`);
    throw new HttpPostError('HTTP POST failed: no response.');
  }
  let parsed: unknown = null;
  try {
    if (response.data === '' || response.data == null) {
      parsed = null;
    } else if (typeof response.data === 'object') {
      parsed = response.data;
    } else if (typeof response.data === 'string') {
      parsed = JSON.parse(response.data) as unknown;
    }
  } catch {
    parsed = null;
  }
  return { statusCode: response.status, body: parsed };
}

/** POST JSON webhook with standard HMAC and tracing headers. */
export async function _httpPostWebhook(
  url: string,
  body: string,
  signature: string,
  deliveryId: string,
): Promise<{ statusCode: number; body: unknown }> {
  const headers: Record<string, string> = {
    'X-Webhook-Signature': signature,
    'X-Webhook-Id': deliveryId,
    'Content-Type': 'application/json',
  };
  return _httpPostWithHeaders(url, body, headers);
}

// ── Discovery ───────────────────────────────────────────────────────────────

export async function _msDiscover(service: string): Promise<string> {
  return _msGetServiceUrl(service);
}

/** A peer's health (`HealthStatus`): up or down. */
export interface HealthStatus {
  status: 'up' | 'down';
}

/** The declared `microserviceClientOps.timeoutSeconds`, in milliseconds. */
const _MS_TIMEOUT_MS = 30000;

/**
 * The health of peer `service`: up when its `/health` answers a 2xx status within the declared
 * client timeout; any other outcome -- an error status, a timeout, a refused connection -- is
 * down. The failure is logged here by its name and never returned: its text names the peer's
 * internal host and port.
 */
export async function _msHealth(service: string): Promise<HealthStatus> {
  const url = _msGetServiceUrl(service);
  try {
    await axios.get(`${url}/health`, { timeout: _MS_TIMEOUT_MS });
  } catch (error: unknown) {
    console.warn(`peer_health_down service=${service} error=${_errorName(error)}`);
    return { status: 'down' };
  }
  return { status: 'up' };
}

/** Whether peer `service` is up (see `_msHealth`). */
export async function _msIsAvailable(service: string): Promise<boolean> {
  return (await _msHealth(service)).status === 'up';
}

export async function _msListServices(): Promise<string[]> {
  return _knownServices();
}

/** The health of every known peer, probed concurrently: a down peer is recorded, never thrown. */
export async function _msHealthCheckAll(): Promise<Record<string, HealthStatus>> {
  const services = await _msListServices();
  const results = await Promise.all(
    services.map(async (svc) => [svc, await _msHealth(svc)] as const),
  );
  return Object.fromEntries(results);
}

// ── Resilience (circuit breaker via opossum) ────────────────────────────────

type _MicroserviceCircuitTask = () => Promise<unknown>;

const _opossumCircuitBreakers = new Map<
  string,
  CircuitBreaker<[_MicroserviceCircuitTask], unknown>
>();

function _getOrCreateMsCircuitBreaker(
  key: string,
  options?: {
    timeout?: number;
    errorThresholdPercentage?: number;
    resetTimeout?: number;
  },
): CircuitBreaker<[_MicroserviceCircuitTask], unknown> {
  let breaker = _opossumCircuitBreakers.get(key);
  if (!breaker) {
    breaker = new CircuitBreaker(
      async (task: _MicroserviceCircuitTask) => task(),
      {
        timeout: options?.timeout ?? 3000,
        errorThresholdPercentage: options?.errorThresholdPercentage ?? 50,
        resetTimeout: options?.resetTimeout ?? 30000,
      },
    );
    _opossumCircuitBreakers.set(key, breaker);
  }
  return breaker;
}

export async function _msWithCircuitBreaker<T>(
  key: string,
  fn: () => Promise<T>,
  options?: {
    timeout?: number;
    errorThresholdPercentage?: number;
    resetTimeout?: number;
  },
): Promise<T> {
  const breaker = _getOrCreateMsCircuitBreaker(key, options);
  const result = await breaker.fire(fn);
  return result as T;
}

export function _msGetCircuitState(key: string): string {
  const breaker = _opossumCircuitBreakers.get(key);
  if (!breaker) {
    return 'CLOSED';
  }
  if (breaker.halfOpen) {
    return 'HALF_OPEN';
  }
  if (breaker.opened) {
    return 'OPEN';
  }
  return 'CLOSED';
}

export function _msResetCircuit(key: string): void {
  const breaker = _opossumCircuitBreakers.get(key);
  if (breaker) {
    breaker.close();
  }
}

export async function _msWithRetry<T>(
  fn: () => Promise<T>,
  attempts: number,
  delayMs = 100,
): Promise<T> {
  for (let i = 0; i < attempts; i++) {
    try {
      return await fn();
    } catch (err) {
      if (i === attempts - 1) throw err;
      await new Promise((r) => setTimeout(r, delayMs));
    }
  }
  throw new Error('_msWithRetry: unreachable');
}

export async function _msWithExponentialBackoff<T>(
  fn: () => Promise<T>,
  attempts: number,
  baseDelayMs = 100,
): Promise<T> {
  for (let i = 0; i < attempts; i++) {
    try {
      return await fn();
    } catch (err) {
      if (i === attempts - 1) throw err;
      await new Promise((r) => setTimeout(r, baseDelayMs * 2 ** i));
    }
  }
  throw new Error('_msWithExponentialBackoff: unreachable');
}

/**
 * Run `fn` for at most `ms` milliseconds, then fail with `DeadlineExceededError`.
 * The work runs under a deadline scope, so a transaction it is still inside past the
 * bound rolls back instead of committing after the caller was told it failed.
 */
export async function _msWithTimeout<T>(
  fn: () => Promise<T>,
  ms: number,
): Promise<T> {
  return runWithDeadline(ms, fn, () => {
    throw new DeadlineExceededError(ms);
  });
}

const _bulkheadSemaphores = new Map<string, { current: number; max: number }>();

export async function _msWithBulkhead<T>(
  key: string,
  fn: () => Promise<T>,
  concurrency = 10,
): Promise<T> {
  let sem = _bulkheadSemaphores.get(key);
  if (!sem) {
    sem = { current: 0, max: concurrency };
    _bulkheadSemaphores.set(key, sem);
  }
  if (sem.current >= sem.max) {
    throw new Error(
      `Bulkhead "${key}" is at capacity (max ${sem.max} concurrent calls).`,
    );
  }
  sem.current++;
  try {
    return await fn();
  } finally {
    sem.current--;
  }
}

// ── Service Registry ─────────────────────────────────────────────────────────

/** Register a peer's base URL in the in-process registry. */
export async function _msRegister(
  service: string,
  endpoint: string,
): Promise<void> {
  _registeredUrls.set(_normalizeServiceName(service), endpoint);
}

/** Remove a peer from the in-process registry. */
export async function _msDeregister(service: string): Promise<void> {
  _registeredUrls.delete(_normalizeServiceName(service));
}

// ── Tracing ──────────────────────────────────────────────────────────────────

export function _msPropagateContext(
  headers: Record<string, string>,
): Record<string, string> {
  return {
    ...headers,
    'x-trace-id': ((global as Record<string, unknown>)._traceId as string) ?? '',
  };
}

export function _msGetTraceId(): string {
  return ((global as Record<string, unknown>)._traceId as string) ?? '';
}

export function _msSetTraceId(id: string): void {
  (global as Record<string, unknown>)._traceId = id;
}

// ── Load Balancing ───────────────────────────────────────────────────────────

const _instances: Record<string, string[]> = (
  global as Record<string, unknown>
)._instances as typeof _instances ?? {};
(global as Record<string, unknown>)._instances = _instances;

export function _msGetNextInstance(service: string): string {
  const list = _instances[service] ?? [_msGetServiceUrl(service)];
  return list[Math.floor(Math.random() * list.length)];
}

export function _msGetAllInstances(service: string): string[] {
  return _instances[service] ?? [_msGetServiceUrl(service)];
}

// ── Rate Limiting ────────────────────────────────────────────────────────────

const _rateLimit: Record<string, { count: number; windowStart: number }> = (
  global as Record<string, unknown>
)._rateLimit as typeof _rateLimit ?? {};
(global as Record<string, unknown>)._rateLimit = _rateLimit;

export async function _msCheckRateLimit(
  key: string,
  maxCount: number,
  windowSec: number,
): Promise<boolean> {
  const now = Math.floor(Date.now() / 1000);
  const bucket = _rateLimit[key] ?? { count: 0, windowStart: now };
  if (now - bucket.windowStart >= windowSec) {
    bucket.windowStart = now;
    bucket.count = 0;
  }
  bucket.count++;
  _rateLimit[key] = bucket;
  return bucket.count <= maxCount;
}

export async function _msGetRateLimitStatus(
  key: string,
): Promise<{ count: number; windowStart: number }> {
  return _rateLimit[key] ?? { count: 0, windowStart: 0 };
}
