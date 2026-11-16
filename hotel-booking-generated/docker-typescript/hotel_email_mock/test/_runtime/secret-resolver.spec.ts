/**
 * Jest spec of the secret resolver runtime module (`src/_runtime/secret-resolver.ts`).
 *
 * The resolver reads an in-memory manifest through an in-memory backend on an advance-able
 * monotonic clock. A declared handle resolves; an undeclared one raises naming logical names
 * only; an absent or blank value raises naming the handle, the backend and the rendered name,
 * never a value; a refresh that fails serves the stale value unless refresh is fail-closed.
 *
 * Shipped by cruftfree-codegen-typescript-core and emitted verbatim. Do not edit manually.
 */
import {
  SecretHandleNotDeclaredError,
  SecretResolutionError,
  createSecretResolver,
} from '../../src/_runtime/secret-resolver';
import type { SecretReference, SecretResolver } from '../../src/_runtime/secret-resolver';

const BACKEND = 'test-backend';
const HANDLE = 'payment_api_key';
const OTHER_HANDLE = 'smtp_password';
const UNDECLARED_HANDLE = 'not_in_manifest';
const RENDERED_NAME = 'shop/payment-api-key';
const VALUE = 'secret-value-v1';
const ROTATED_VALUE = 'secret-value-v2';
const TTL_SECONDS = 60;
const THROTTLE_MS = 1000;
const NANOSECONDS_PER_SECOND = 1_000_000_000n;

/** A deterministic monotonic clock. */
class AdvanceableClock {
  private nowNs = 0n;

  readonly now = (): bigint => this.nowNs;

  advance(seconds: number): void {
    this.nowNs += BigInt(seconds) * NANOSECONDS_PER_SECOND;
  }
}

/** Values by rendered name, an outage switch and a read count. */
class InMemoryBackend {
  readonly values = new Map<string, string>();
  failing = false;
  reads = 0;

  readonly fetch = async (entry: SecretReference): Promise<string | undefined> => {
    this.reads += 1;
    if (this.failing) {
      throw new Error('backend unavailable');
    }
    return this.values.get(entry.renderedName);
  };
}

interface Fixture {
  readonly resolver: SecretResolver;
  readonly backend: InMemoryBackend;
  readonly clock: AdvanceableClock;
}

function resolverWith(failClosedOnRefresh: boolean, ttlSeconds: number = TTL_SECONDS): Fixture {
  const backend = new InMemoryBackend();
  const clock = new AdvanceableClock();
  const references = new Map<string, SecretReference>([
    [HANDLE, { renderedName: RENDERED_NAME, ttlSeconds }],
    [OTHER_HANDLE, { renderedName: 'shop/smtp-password', ttlSeconds }],
  ]);
  const resolver = createSecretResolver({
    references,
    fetchSecret: backend.fetch,
    backend: BACKEND,
    failClosedOnRefresh,
    invalidationThrottleMs: THROTTLE_MS,
    clock: clock.now,
  });
  return { resolver, backend, clock };
}

describe('secret resolver', () => {
  it('resolves a declared handle and serves it from the cache within its TTL', async () => {
    const { resolver, backend, clock } = resolverWith(false);
    backend.values.set(RENDERED_NAME, VALUE);

    expect(await resolver.getSecret(HANDLE)).toBe(VALUE);
    clock.advance(TTL_SECONDS - 1);
    expect(await resolver.getSecret(HANDLE)).toBe(VALUE);
    expect(backend.reads).toBe(1);
  });

  it('refuses an undeclared handle naming logical names only', async () => {
    const { resolver, backend } = resolverWith(false);
    backend.values.set(RENDERED_NAME, VALUE);

    const refusal = resolver.getSecret(UNDECLARED_HANDLE);

    await expect(refusal).rejects.toBeInstanceOf(SecretHandleNotDeclaredError);
    const error = (await refusal.catch((caught: unknown) => caught)) as SecretHandleNotDeclaredError;
    expect(error.handle).toBe(UNDECLARED_HANDLE);
    expect(error.declared).toEqual([HANDLE, OTHER_HANDLE]);
    expect(error.message).toContain(`'${UNDECLARED_HANDLE}'`);
    expect(error.message).not.toContain(VALUE);
    expect(backend.reads).toBe(0);
  });

  it.each([
    ['absent', undefined],
    ['blank', '   '],
  ])('refuses an %s value naming the handle, backend and rendered name', async (_case, stored) => {
    const { resolver, backend } = resolverWith(false);
    if (stored !== undefined) {
      backend.values.set(RENDERED_NAME, stored);
    }

    const refusal = resolver.getSecret(HANDLE);

    await expect(refusal).rejects.toBeInstanceOf(SecretResolutionError);
    const error = (await refusal.catch((caught: unknown) => caught)) as SecretResolutionError;
    expect([error.handle, error.backend, error.renderedName]).toEqual([HANDLE, BACKEND, RENDERED_NAME]);
  });

  it('propagates a backend failure when no value was ever resolved', async () => {
    const { resolver, backend } = resolverWith(false);
    backend.failing = true;

    await expect(resolver.getSecret(HANDLE)).rejects.toThrow('backend unavailable');
  });

  it('refetches after the TTL and shares one fetch between concurrent misses', async () => {
    const { resolver, backend, clock } = resolverWith(false);
    backend.values.set(RENDERED_NAME, VALUE);
    await resolver.getSecret(HANDLE);
    clock.advance(TTL_SECONDS + 1);
    backend.values.set(RENDERED_NAME, ROTATED_VALUE);

    const values = await Promise.all([resolver.getSecret(HANDLE), resolver.getSecret(HANDLE), resolver.getSecret(HANDLE)]);

    expect(values).toEqual([ROTATED_VALUE, ROTATED_VALUE, ROTATED_VALUE]);
    expect(backend.reads).toBe(2);
  });

  it('never expires a value cached with a zero TTL', async () => {
    const { resolver, backend, clock } = resolverWith(false, 0);
    backend.values.set(RENDERED_NAME, VALUE);
    await resolver.getSecret(HANDLE);
    clock.advance(1_000_000);

    expect(await resolver.getSecret(HANDLE)).toBe(VALUE);
    expect(backend.reads).toBe(1);
  });

  it('serves the stale value when a refresh fails', async () => {
    const { resolver, backend, clock } = resolverWith(false);
    backend.values.set(RENDERED_NAME, VALUE);
    await resolver.getSecret(HANDLE);
    clock.advance(TTL_SECONDS + 1);
    backend.failing = true;

    expect(await resolver.getSecret(HANDLE)).toBe(VALUE);
  });

  it('serves the stale value when a refresh finds the value gone', async () => {
    const { resolver, backend, clock } = resolverWith(false);
    backend.values.set(RENDERED_NAME, VALUE);
    await resolver.getSecret(HANDLE);
    clock.advance(TTL_SECONDS + 1);
    backend.values.delete(RENDERED_NAME);

    expect(await resolver.getSecret(HANDLE)).toBe(VALUE);
  });

  it('refuses a failed or absent refresh under fail-closed refresh', async () => {
    const { resolver, backend, clock } = resolverWith(true);
    backend.values.set(RENDERED_NAME, VALUE);
    await resolver.getSecret(HANDLE);
    clock.advance(TTL_SECONDS + 1);
    backend.failing = true;

    await expect(resolver.getSecret(HANDLE)).rejects.toThrow('backend unavailable');
    backend.failing = false;
    backend.values.delete(RENDERED_NAME);
    await expect(resolver.getSecret(HANDLE)).rejects.toBeInstanceOf(SecretResolutionError);
  });

  it('refetches once after an invalidation and throttles a second one', async () => {
    const { resolver, backend } = resolverWith(false);
    backend.values.set(RENDERED_NAME, VALUE);
    await resolver.getSecret(HANDLE);
    backend.values.set(RENDERED_NAME, ROTATED_VALUE);

    resolver.invalidateSecret(HANDLE, 'credential-rejected');
    expect(await resolver.getSecret(HANDLE)).toBe(ROTATED_VALUE);
    backend.values.set(RENDERED_NAME, VALUE);
    resolver.invalidateSecret(HANDLE, 'credential-rejected');

    expect(await resolver.getSecret(HANDLE)).toBe(ROTATED_VALUE);
    expect(backend.reads).toBe(2);
  });

  it('refuses to invalidate an undeclared handle', () => {
    const { resolver } = resolverWith(false);

    expect(() => resolver.invalidateSecret(UNDECLARED_HANDLE, 'credential-rejected')).toThrow(
      SecretHandleNotDeclaredError,
    );
  });
});
