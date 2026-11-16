import { Logger } from '@nestjs/common';
import { AsyncLocalStorage } from 'node:async_hooks';

/**
 * Raised by `throwIfDeadlinePassed` when work that outlived its bound reaches a
 * point it must not complete from, and by `Microservice.withTimeout` past its bound.
 */
export class DeadlineExceededError extends Error {
  constructor(readonly boundMs: number) {
    super(`Work did not complete within ${boundMs}ms`);
    this.name = 'DeadlineExceededError';
  }
}

interface DeadlineScope {
  readonly boundMs: number;
  readonly parent: DeadlineScope | undefined;
  expired: boolean;
}

const deadlineScope = new AsyncLocalStorage<DeadlineScope>();

/** The marker the expiry of one `runWithDeadline` resolves with, so only that bound answers. */
const EXPIRED: unique symbol = Symbol('deadline-expired');

/**
 * Run `work` for at most `boundMs` milliseconds. Past the bound the scope is marked
 * expired and `onExpiry` answers at once. JavaScript cannot stop work already
 * running, so the work is stopped cooperatively: every `transaction(...)` unit the
 * work is inside checks its scopes (`deadlineBounded`) before it commits, throws,
 * and rolls back. A deadline nested in the work that expires reaches this caller as
 * the work's own failure, never as this bound's expiry.
 */
export async function runWithDeadline<T>(
  boundMs: number,
  work: () => Promise<T>,
  onExpiry: () => T | Promise<T>,
): Promise<T> {
  const scope: DeadlineScope = { boundMs, parent: deadlineScope.getStore(), expired: false };
  let timer: ReturnType<typeof setTimeout> | undefined;
  const expiry = new Promise<typeof EXPIRED>((resolve) => {
    timer = setTimeout(() => {
      scope.expired = true;
      resolve(EXPIRED);
    }, boundMs);
  });
  let outcome: T | typeof EXPIRED;
  try {
    outcome = await Promise.race([deadlineScope.run(scope, work), expiry]);
  } finally {
    if (timer !== undefined) {
      clearTimeout(timer);
    }
  }
  return outcome === EXPIRED ? await onExpiry() : outcome;
}

const deadlineLogger = new Logger('EndpointDeadline');

/** Log that a fallback answered a route (its matched pattern) whose handler ran past its bound. */
export function logDeadlineFallback(method: string, route: string, boundMs: number): void {
  deadlineLogger.warn(`endpoint_deadline_fallback method=${method} endpoint=${route} bound_ms=${boundMs}`);
}

/** Throw `DeadlineExceededError` when the bound of the running work, or of any work it runs inside, has passed. */
export function throwIfDeadlinePassed(): void {
  for (let scope = deadlineScope.getStore(); scope !== undefined; scope = scope.parent) {
    if (scope.expired) {
      throw new DeadlineExceededError(scope.boundMs);
    }
  }
}

/**
 * Wrap the callback of a transaction unit so that work which outlived its bound
 * throws before the unit commits, which rolls the unit back.
 */
export function deadlineBounded<A extends unknown[], R>(
  unit: (...args: A) => Promise<R>,
): (...args: A) => Promise<R> {
  return async (...args: A): Promise<R> => {
    const result = await unit(...args);
    throwIfDeadlinePassed();
    return result;
  };
}
