/**
 * Seed data for emailDb component.
 *
 * Auto-generated from .cseed seed declarations. Do not edit manually.
 */
import { MikroORM, EntityManager } from '@mikro-orm/core';
import type { AbstractSqlConnection } from '@mikro-orm/postgresql';
import { ApiKey } from '../../hotel_email_mock/entities/email_db/api-key.entity';

type SeedLookupValue = {
  __seedLookup: true;
  entityName: string;
  matchFields: Record<string, unknown>;
};

const ENTITY_BY_NAME = {
  ApiKey,
} as const;

/** The block lock's statements, spelled by the database's dialect, and its wait budget. */
const SESSION_LOCK = {
  tryAcquire: "SELECT pg_try_advisory_lock(hashtext(\u0027b7c2d91e-5f34-4a06-8e27-1c6a9f4d3b52\u0027))",
  release: "SELECT pg_advisory_unlock(hashtext(\u0027b7c2d91e-5f34-4a06-8e27-1c6a9f4d3b52\u0027))",
  acquired: true,
  retryMs: 2000,
  maxAttempts: 20,
} as const;

type LockQueryResult = { rows?: unknown[] } | unknown[];

/** The one scalar a lock statement returns, whichever driver shaped the result. */
function lockAnswer(result: LockQueryResult): unknown {
  const rows = Array.isArray(result) ? (Array.isArray(result[0]) ? (result[0] as unknown[]) : result) : result.rows;
  const first = rows?.[0];
  if (first === undefined || first === null || typeof first !== 'object') {
    throw new Error(`Seed component emailDb: the block lock statement returned no row.`);
  }
  return Object.values(first as Record<string, unknown>)[0];
}

/**
 * Runs *work* holding the block lock on a dedicated connection of *orm*: a bounded
 * number of non-blocking attempts, then a failure naming the lock, so a stuck holder cannot
 * wedge this process forever. The lock lives on its own session, so it is released when that
 * session ends even if this process dies while holding it.
 */
async function withSessionLock<T>(orm: MikroORM, work: () => Promise<T>): Promise<T> {
  const knex = (orm.em.getConnection() as AbstractSqlConnection).getKnex();
  const lockConnection = await knex.client.acquireConnection();
  try {
    let acquired = false;
    for (let attempt = 1; attempt <= SESSION_LOCK.maxAttempts; attempt += 1) {
      const answer = lockAnswer(await knex.raw(SESSION_LOCK.tryAcquire).connection(lockConnection));
      if (answer === null || answer === undefined) {
        throw new Error(
          `Seed component emailDb: the database returned NULL for the block lock; ` +
            `it did not say whether the lock was obtained, so nothing was run.`,
        );
      }
      if (answer === SESSION_LOCK.acquired) {
        acquired = true;
        break;
      }
      await new Promise((resolve) => setTimeout(resolve, SESSION_LOCK.retryMs));
    }
    if (!acquired) {
      throw new Error(
        `Seed component emailDb: could not acquire the block lock after ` +
          `${SESSION_LOCK.maxAttempts} attempts; another replica or consumer may be stuck ` +
          `holding it. Restart to retry.`,
      );
    }
    try {
      return await work();
    } finally {
      // Cleanup must never mask the primary failure; the session ending frees the lock.
      try {
        await knex.raw(SESSION_LOCK.release).connection(lockConnection);
      } catch (error) {
        console.warn(`session_unlock_failed lock=block error=${String(error)}`);
      }
    }
  } finally {
    knex.client.releaseConnection(lockConnection);
  }
}

function isSeedLookupValue(value: unknown): value is SeedLookupValue {
  return (
    typeof value === 'object' &&
    value !== null &&
    (value as { __seedLookup?: unknown }).__seedLookup === true
  );
}

async function resolveSeedLookups(
  em: EntityManager,
  row: Record<string, unknown>,
): Promise<Record<string, unknown>> {
  const resolved: Record<string, unknown> = { ...row };

  for (const [fieldName, value] of Object.entries(row)) {
    if (!isSeedLookupValue(value)) {
      continue;
    }

    const entityClass = ENTITY_BY_NAME[value.entityName as keyof typeof ENTITY_BY_NAME];
    if (entityClass === undefined) {
      throw new Error(`Seed lookup for ${fieldName} references unknown entity '${value.entityName}'`);
    }

    const found = await em.findOne(entityClass, value.matchFields);
    if (found === null) {
      throw new Error(
        `Seed lookup for ${fieldName} could not find ${value.entityName} with ${JSON.stringify(value.matchFields)}`,
      );
    }

    resolved[fieldName] = (found as { id?: unknown }).id;
  }

  return resolved;
}

/**
 * Seed emailDb component with the categories its generated profile runs.
 *
 * @param orm - MikroORM instance
 * @param profile - Deployment profile (logged; the categories were fixed at generation)
 * @param reset - Delete the rows of every table this component seeds
 *   (reverse seed order, children first) before seeding */
export async function seedEmailDb(orm: MikroORM, profile: string, reset: boolean): Promise<void> {
  // The block's rows are written by every service that writes it: seeding holds the
  // block's session lock, so a seed never interleaves with another writer's seed of it.
  await withSessionLock(orm, () => seedEmailDbLocked(orm, profile, reset));
}

async function seedEmailDbLocked(orm: MikroORM, profile: string, reset: boolean): Promise<void> {
  const em = orm.em.fork();
  console.log(`[SeedEmailDb] Seeding emailDb for profile '${profile}' reset=${reset}`);

  if (reset) {
    await em.nativeDelete(ApiKey, {});
    console.log(`[SeedEmailDb] seed_reset_completed component=emailDb`);
  }

  // baseline data: the generated profile runs this category
  {
    // Seed ApiKey (conflict on: keyHash; an existing row is
    // left as it is)
    for (const row of baselineRowsApiKey) {
      const resolvedRow = await resolveSeedLookups(em, row);
      await em.upsert(ApiKey, resolvedRow, {
        onConflictFields: ["keyHash"],
        onConflictAction: 'ignore',
      });
    }

  }

  await em.flush();
  console.log(`[SeedEmailDb] Completed seeding emailDb`);
}

// baseline / ApiKey
const baselineRowsApiKey = [{"id": "a2188c9e-0210-5b65-9aaa-b5212c89335c", "keyHash": "8ebb0f49fb77982872cbe7909a416457f2e847b42cfc3cbb84abdeede8163761", "ownerId": "cfd33215-9eeb-565d-b468-edd0282279fb"}] as readonly Record<string, unknown>[];

