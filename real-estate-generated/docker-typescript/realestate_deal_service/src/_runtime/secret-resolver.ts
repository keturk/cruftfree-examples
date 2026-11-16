/**
 * Secret resolver core -- resolves a logical secret handle to its value.
 *
 * A handle resolves through the backend the deployment target declared, under the name
 * and from the store the application placement gave it. Nothing here reads the process
 * environment, holds a secret value outside the cache, or defaults one.
 *
 * Each handle is cached for its own TTL on a monotonic clock (immune to wall-clock
 * jumps). Concurrent misses for one handle share one fetch. A refresh that fails while
 * a prior value is cached serves the stale value with a warning, unless the deployment
 * opted into fail-closed refresh; a handle with no prior value and a failed or absent
 * fetch always throws.
 *
 * The manifest, the backend fetch, the backend name, the refresh policy, the
 * invalidation throttle and the clock are the project-specific values: parameters of
 * `createSecretResolver`, which the service's `secrets/secrets.service.ts` binding
 * passes. One resolver serves the whole process, so every reader shares its cache.
 *
 * Shipped by cruftfree-codegen-typescript-core and emitted verbatim. Do not edit manually.
 */
import { Logger } from '@nestjs/common';

const NANOSECONDS_PER_SECOND = 1_000_000_000n;
const NANOSECONDS_PER_MILLISECOND = 1_000_000n;

/**
 * Fail-closed secret-resolution failure: thrown before any value is returned. The message
 * carries the logical handle, the backend and the rendered name only -- never a value.
 */
export class SecretResolutionError extends Error {
  constructor(
    readonly handle: string,
    readonly backend: string,
    readonly renderedName: string,
  ) {
    super(
      `Required secret '${handle}' not found in backend '${backend}' (absent or blank). ` +
        `Ensure a non-blank secret is provisioned in the deployment environment with the ` +
        `rendered name '${renderedName}'.`,
    );
    this.name = 'SecretResolutionError';
  }
}

/**
 * A handle the generated manifest does not declare: a code-generation error, never a
 * deployment problem.
 */
export class SecretHandleNotDeclaredError extends Error {
  constructor(
    readonly handle: string,
    readonly declared: readonly string[],
  ) {
    super(
      `Secret handle '${handle}' is not declared in the generated secrets manifest. ` +
        `Declared handles: ${declared.join(', ')}. This is a code-generation error — ` +
        `regenerate the service so the resolver and manifest are built from the same ` +
        `service definition.`,
    );
    this.name = 'SecretHandleNotDeclaredError';
  }
}

/** What resolution reads of one manifest entry. */
export interface SecretReference {
  readonly renderedName: string;
  /** Seconds a resolved value stays cached; `0` never expires. */
  readonly ttlSeconds: number;
}

/** Everything project-specific the resolver needs, passed by the service's binding. */
export interface SecretResolverOptions<TEntry extends SecretReference> {
  /** The generated manifest: every declared handle and its entry. */
  readonly references: ReadonlyMap<string, TEntry>;
  /** Reads one secret from the deployment's backend; `undefined` when it holds none. */
  readonly fetchSecret: (entry: TEntry) => Promise<string | undefined>;
  /** The backend's name, reported in logs and errors. */
  readonly backend: string;
  /** Whether a failed refresh refuses instead of serving the stale value. */
  readonly failClosedOnRefresh: boolean;
  /** The shortest interval between two evictions of one handle. */
  readonly invalidationThrottleMs: number;
  /** Monotonic nanoseconds: not related to the time of day, so not subject to clock drift. */
  readonly clock: () => bigint;
}

/** What a service's binding exports. */
export interface SecretResolver {
  /**
   * Resolve `handle` to its value. Never returns an absent or blank value: a keyed hash
   * or comparison under an empty secret is forgeable by any caller.
   */
  readonly getSecret: (handle: string) => Promise<string>;
  /**
   * Evict `handle` from the cache so the next `getSecret` refetches it.
   *
   * For generated credential-aware wrappers ONLY: a wrapper that classifies a downstream
   * error as a DEFINITIVE credential failure (an authentication-rejected response) calls
   * this to drop the stale credential before its TTL expires, then retries the original
   * operation at most once. A transient or non-credential error must never call it.
   *
   * The eviction is idempotent and throttled per handle; the `getSecret` that follows is the
   * single refetch, shared by concurrent callers. This function never loops, never retries
   * on its own and never logs a value.
   *
   * @throws {SecretHandleNotDeclaredError} When the manifest does not declare `handle`: the
   *   wrapper names a handle no deployment provisions, which is a generation defect.
   */
  readonly invalidateSecret: (handle: string, reason: string) => void;
}

interface CachedSecret {
  readonly value: string;
  /** The clock reading at which the value expires; `undefined` never expires. */
  readonly expiresAt: bigint | undefined;
}

/** The secret resolver of one service, reading its manifest through its backend. */
export function createSecretResolver<TEntry extends SecretReference>(
  options: SecretResolverOptions<TEntry>,
): SecretResolver {
  const cache = new Map<string, CachedSecret>();
  const inFlight = new Map<string, Promise<string>>();
  const lastInvalidatedAt = new Map<string, bigint>();
  const logger = new Logger('SecretsService');
  const invalidationLogger = new Logger('SecretsInvalidation');

  function notDeclared(handle: string): SecretHandleNotDeclaredError {
    return new SecretHandleNotDeclaredError(handle, [...options.references.keys()].sort());
  }

  async function refresh(handle: string, entry: TEntry, stale: CachedSecret | undefined): Promise<string> {
    let fetched: string | undefined;
    try {
      fetched = await options.fetchSecret(entry);
    } catch (error) {
      if (stale !== undefined && !options.failClosedOnRefresh) {
        logger.warn(
          `secret_refresh_failed_serving_stale backend=${options.backend} handle=${handle} ` +
            `error=${error instanceof Error ? error.constructor.name : typeof error}`,
        );
        return stale.value;
      }
      throw error;
    }
    if (fetched === undefined || fetched.trim() === '') {
      if (stale !== undefined && !options.failClosedOnRefresh) {
        logger.warn(`secret_refresh_absent_serving_stale backend=${options.backend} handle=${handle}`);
        return stale.value;
      }
      throw new SecretResolutionError(handle, options.backend, entry.renderedName);
    }
    cache.set(handle, {
      value: fetched,
      expiresAt:
        entry.ttlSeconds === 0 ? undefined : options.clock() + BigInt(entry.ttlSeconds) * NANOSECONDS_PER_SECOND,
    });
    logger.log(`secret_resolved backend=${options.backend} handle=${handle}`);
    return fetched;
  }

  async function getSecret(handle: string): Promise<string> {
    const entry = options.references.get(handle);
    if (entry === undefined) {
      throw notDeclared(handle);
    }
    const cached = cache.get(handle);
    if (cached !== undefined && (cached.expiresAt === undefined || options.clock() < cached.expiresAt)) {
      return cached.value;
    }
    const pending = inFlight.get(handle);
    if (pending !== undefined) {
      return pending;
    }
    const fetched = refresh(handle, entry, cached).finally(() => {
      inFlight.delete(handle);
    });
    inFlight.set(handle, fetched);
    return fetched;
  }

  function invalidateSecret(handle: string, reason: string): void {
    if (!options.references.has(handle)) {
      throw notDeclared(handle);
    }
    const at = options.clock();
    const previous = lastInvalidatedAt.get(handle);
    if (previous !== undefined && at - previous < BigInt(options.invalidationThrottleMs) * NANOSECONDS_PER_MILLISECOND) {
      invalidationLogger.warn(
        `secret_invalidation_throttled backend=${options.backend} handle=${handle} reason=${reason}`,
      );
      return;
    }
    lastInvalidatedAt.set(handle, at);
    if (cache.delete(handle)) {
      invalidationLogger.warn(`secret_invalidated backend=${options.backend} handle=${handle} reason=${reason}`);
    }
  }

  return { getSecret, invalidateSecret };
}
