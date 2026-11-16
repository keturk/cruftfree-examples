/**
 * Seed data for viewingDb component.
 *
 * Auto-generated from .cseed seed declarations. Do not edit manually.
 */
import { MikroORM, EntityManager } from '@mikro-orm/core';
import type { AbstractSqlConnection } from '@mikro-orm/postgresql';
import { Viewing } from '../../realestate_viewing_service/entities/viewing_db/viewing.entity';

type SeedLookupValue = {
  __seedLookup: true;
  entityName: string;
  matchFields: Record<string, unknown>;
};

const ENTITY_BY_NAME = {
  Viewing,
} as const;

type SeedRelativeValue = {
  __seedRelative: true;
  kind: 'date' | 'datetime';
  months: number;
  days: number;
  hour: number;
  minute: number;
  zone: string;
};

const MS_PER_DAY = 86_400_000;
const MS_PER_MINUTE = 60_000;

function isSeedRelativeValue(value: unknown): value is SeedRelativeValue {
  return (
    typeof value === 'object' &&
    value !== null &&
    (value as { __seedRelative?: unknown }).__seedRelative === true
  );
}

/** The anchor moved by calendar months (the day clamped to the month's end), then days; UTC midnight. */
function shiftSeedDate(anchor: Date, months: number, days: number): Date {
  const total = anchor.getUTCFullYear() * 12 + anchor.getUTCMonth() + months;
  const year = Math.floor(total / 12);
  const month = total - year * 12;
  const lastDay = new Date(Date.UTC(year, month + 1, 0)).getUTCDate();
  return new Date(Date.UTC(year, month, Math.min(anchor.getUTCDate(), lastDay) + days));
}

/** The zone's UTC offset in minutes at an instant. */
function zoneOffsetMinutes(instantMs: number, zone: string): number {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: zone,
    hourCycle: 'h23',
    year: 'numeric',
    month: 'numeric',
    day: 'numeric',
    hour: 'numeric',
    minute: 'numeric',
    second: 'numeric',
  }).formatToParts(new Date(instantMs));
  const part = (type: string): number => Number(parts.find((candidate) => candidate.type === type)?.value);
  const wallAsUtc = Date.UTC(part('year'), part('month') - 1, part('day'), part('hour'), part('minute'), part('second'));
  return Math.round((wallAsUtc - Math.floor(instantMs / 1000) * 1000) / MS_PER_MINUTE);
}

/**
 * The instant at which the zone's wall clock reads the given time. A wall time the zone repeats
 * is the earlier instant; one it skips is read with the offset in force before the transition.
 */
function zonedWallTimeToInstant(wallAsUtc: number, zone: string): number {
  if (zone === 'UTC') {
    return wallAsUtc;
  }
  const before = zoneOffsetMinutes(wallAsUtc - MS_PER_DAY, zone) * MS_PER_MINUTE;
  const after = zoneOffsetMinutes(wallAsUtc + MS_PER_DAY, zone) * MS_PER_MINUTE;
  const instants = [before, after]
    .filter((offset, index, offsets) => offsets.indexOf(offset) === index)
    .filter((offset) => zoneOffsetMinutes(wallAsUtc - offset, zone) * MS_PER_MINUTE === offset)
    .map((offset) => wallAsUtc - offset);
  return instants.length > 0 ? Math.min(...instants) : wallAsUtc - before;
}

/** '@date' as 'YYYY-MM-DD'; '@datetime' as the UTC instant 'YYYY-MM-DDTHH:MM:SS.000Z'. */
function evaluateSeedRelative(value: SeedRelativeValue, anchor: Date): string {
  const shifted = shiftSeedDate(anchor, value.months, value.days);
  if (value.kind === 'date') {
    return shifted.toISOString().slice(0, 10);
  }
  const wall = Date.UTC(shifted.getUTCFullYear(), shifted.getUTCMonth(), shifted.getUTCDate(), value.hour, value.minute);
  return new Date(zonedWallTimeToInstant(wall, value.zone)).toISOString();
}

/** Every relative date in the value (a row, a lookup's match fields, a document or item) as the value it has at the anchor. */
function resolveSeedRelatives(value: unknown, anchor: Date): unknown {
  if (isSeedRelativeValue(value)) {
    return evaluateSeedRelative(value, anchor);
  }
  if (Array.isArray(value)) {
    return value.map((inner) => resolveSeedRelatives(inner, anchor));
  }
  if (typeof value === 'object' && value !== null) {
    return Object.fromEntries(
      Object.entries(value).map(([key, inner]) => [key, resolveSeedRelatives(inner, anchor)]),
    );
  }
  return value;
}

/** The block lock's statements, spelled by the database's dialect, and its wait budget. */
const SESSION_LOCK = {
  tryAcquire: "SELECT pg_try_advisory_lock(hashtext(\u0027ec0977bd-086f-4670-a383-76b48d4b4dfb\u0027))",
  release: "SELECT pg_advisory_unlock(hashtext(\u0027ec0977bd-086f-4670-a383-76b48d4b4dfb\u0027))",
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
    throw new Error(`Seed component viewingDb: the block lock statement returned no row.`);
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
          `Seed component viewingDb: the database returned NULL for the block lock; ` +
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
        `Seed component viewingDb: could not acquire the block lock after ` +
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
 * Seed viewingDb component with the categories its generated profile runs.
 *
 * @param orm - MikroORM instance
 * @param profile - Deployment profile (logged; the categories were fixed at generation)
 * @param reset - Delete the rows of every table this component seeds
 *   (reverse seed order, children first) before seeding * @param anchor - The 'YYYY-MM-DD' date every relative @date / @datetime is evaluated against
 */
export async function seedViewingDb(orm: MikroORM, profile: string, reset: boolean, anchor: string): Promise<void> {
  // The block's rows are written by every service that writes it: seeding holds the
  // block's session lock, so a seed never interleaves with another writer's seed of it.
  await withSessionLock(orm, () => seedViewingDbLocked(orm, profile, reset, anchor));
}

async function seedViewingDbLocked(orm: MikroORM, profile: string, reset: boolean, anchor: string): Promise<void> {
  const anchorDate = new Date(`${anchor}T00:00:00Z`);
  console.log(`[SeedViewingDb] seed_anchor_resolved component=viewingDb anchor=${anchor}`);
  const em = orm.em.fork();
  console.log(`[SeedViewingDb] Seeding viewingDb for profile '${profile}' reset=${reset}`);

  if (reset) {
    await em.nativeDelete(Viewing, {});
    console.log(`[SeedViewingDb] seed_reset_completed component=viewingDb`);
  }

  // baseline data: the generated profile runs this category
  {
    // Seed Viewing (conflict on: id; an existing row is
    // left as it is)
    for (const row of baselineRowsViewing) {
      const resolvedRow = await resolveSeedLookups(em, resolveSeedRelatives(row, anchorDate) as Record<string, unknown>);
      await em.upsert(Viewing, resolvedRow, {
        onConflictFields: ["id"],
        onConflictAction: 'ignore',
      });
    }

  }

  await em.flush();
  console.log(`[SeedViewingDb] Completed seeding viewingDb`);
}

// baseline / Viewing
const baselineRowsViewing = [{"id": "1793016e-b3ad-548f-9e55-3b1f4343231e", "listingId": "618dd1a8-4d40-5d45-9e8a-5ad3059cdb15", "listingTitle": "Rose Street bungalow", "buyerName": "Theo Marsh", "buyerEmail": "theo@example.com", "agentName": "Dana Whitlock", "agentEmail": "dana@cobblestone.example.com", "startsAt": {"__seedRelative": true, "kind": "datetime", "months": 0, "days": 2, "hour": 10, "minute": 0, "zone": "UTC"}, "endsAt": {"__seedRelative": true, "kind": "datetime", "months": 0, "days": 2, "hour": 10, "minute": 30, "zone": "UTC"}, "status": "Requested", "note": "Could we see the garden too?"}, {"id": "76eb2c4d-4606-5758-8d7d-1d52db108a32", "listingId": "db431b5b-cc77-532b-a3fe-c824802832b4", "listingTitle": "Loft over the old mill", "buyerName": "Mara Oyelaran", "buyerEmail": "mara@example.com", "agentName": "Dana Whitlock", "agentEmail": "dana@cobblestone.example.com", "startsAt": {"__seedRelative": true, "kind": "datetime", "months": 0, "days": 1, "hour": 15, "minute": 0, "zone": "UTC"}, "endsAt": {"__seedRelative": true, "kind": "datetime", "months": 0, "days": 1, "hour": 15, "minute": 30, "zone": "UTC"}, "status": "Confirmed", "note": null}] as readonly Record<string, unknown>[];

