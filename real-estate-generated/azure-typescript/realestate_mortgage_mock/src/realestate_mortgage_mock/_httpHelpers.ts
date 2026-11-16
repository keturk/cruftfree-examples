/**
 * Http helper for generated TypeScript code: every `Http` builtin call routes here,
 * so one request policy holds on every call:
 *
 * - the result is an `HttpResponse` with `status`, `headers`, `body` (the raw bytes),
 *   `text` and `json`;
 * - a status outside 200-299 throws `HttpCallError`, never returns as a value, so a
 *   failed call cannot be mistaken for a result;
 * - a failure names the method and the status, never the URL: its query can hold an
 *   API key, and an axios error's `config` holds the URL and the request headers;
 * - a call without a `timeout` option times out after `HTTP_DEFAULT_TIMEOUT_SECONDS`.
 *
 * `options` is a map with a closed set of keys: `headers` (a map of header name to
 * value), `timeout` (seconds, a number) and `retries` (the number of extra attempts
 * after a failed connection). Any other key throws, and TLS certificate verification
 * is never configurable.
 */
import axios, { type AxiosRequestConfig } from 'axios';

const HTTP_OPTION_KEYS: readonly string[] = ['headers', 'timeout', 'retries'];

/** Seconds a request may take when the call names no `timeout` option. */
const HTTP_DEFAULT_TIMEOUT_SECONDS = 30;

/** Connection-level failures where the request never reached the server. */
const RETRYABLE_CONNECTION_CODES: ReadonlySet<string> = new Set([
  'ECONNREFUSED',
  'ENOTFOUND',
  'EAI_AGAIN',
  'ETIMEDOUT',
]);

/**
 * An `Http` call failed: names the method and the status, never the URL. `status` is
 * undefined when the server gave no response (a refused connection, a timeout).
 */
export class HttpCallError extends Error {
  readonly method: string;
  readonly status: number | undefined;

  constructor(method: string, status: number | undefined) {
    const outcome = status === undefined ? 'no response' : `status ${status}`;
    super(`Http ${method} call failed: ${outcome}.`);
    this.name = 'HttpCallError';
    this.method = method;
    this.status = status;
  }
}

/** The typed error of a failed axios request: reads only the status, never the error's text. */
function _httpCallError(method: string, error: unknown): HttpCallError {
  return new HttpCallError(method, axios.isAxiosError(error) ? error.response?.status : undefined);
}

/** The response of an `Http` call. */
export class HttpResponse {
  constructor(
    readonly status: number,
    readonly headers: Record<string, string>,
    readonly body: Buffer,
  ) {}

  /** The body decoded as UTF-8. */
  get text(): string {
    return this.body.toString('utf-8');
  }

  /** The body parsed as JSON; throws when it is not valid JSON. */
  get json(): unknown {
    return JSON.parse(this.text) as unknown;
  }
}

export async function _httpRequest(
  method: string,
  url: string,
  body: unknown,
  options: Record<string, unknown>,
): Promise<HttpResponse> {
  const unknownKeys = Object.keys(options).filter((key) => !HTTP_OPTION_KEYS.includes(key));
  if (unknownKeys.length > 0) {
    throw new Error(
      `Http options ${JSON.stringify(unknownKeys.sort())} are not supported; ` +
        `valid options: ${JSON.stringify([...HTTP_OPTION_KEYS].sort())}`,
    );
  }
  const headers = options.headers;
  if (headers !== undefined && headers !== null && (typeof headers !== 'object' || Array.isArray(headers))) {
    throw new Error("Http option 'headers' must be a map of header name to value");
  }
  const timeout = options.timeout;
  if (timeout !== undefined && timeout !== null && (typeof timeout !== 'number' || !Number.isFinite(timeout))) {
    throw new Error("Http option 'timeout' must be a number of seconds");
  }
  const retries = options.retries ?? 0;
  if (typeof retries !== 'number' || !Number.isInteger(retries) || retries < 0) {
    throw new Error(`Http option 'retries' must be a non-negative integer, got ${String(retries)}`);
  }
  const config: AxiosRequestConfig = {
    method,
    url,
    data: body,
    headers: (headers ?? undefined) as Record<string, string> | undefined,
    timeout: (typeof timeout === 'number' ? timeout : HTTP_DEFAULT_TIMEOUT_SECONDS) * 1000,
    // The body is handed over as raw bytes; `HttpResponse` decodes it on demand.
    responseType: 'arraybuffer',
    transformResponse: (data: unknown) => data,
    validateStatus: (status: number) => status >= 200 && status < 300,
  };
  for (let attempt = 0; ; attempt += 1) {
    try {
      const response = await axios.request<ArrayBuffer>(config);
      return new HttpResponse(
        response.status,
        Object.fromEntries(
          Object.entries(response.headers).map(([name, value]) => [name.toLowerCase(), String(value)]),
        ),
        Buffer.from(response.data),
      );
    } catch (error) {
      const connectionFailure =
        axios.isAxiosError(error) &&
        error.response === undefined &&
        RETRYABLE_CONNECTION_CODES.has(error.code ?? '');
      if (!connectionFailure || attempt >= retries) {
        throw _httpCallError(method, error);
      }
    }
  }
}
