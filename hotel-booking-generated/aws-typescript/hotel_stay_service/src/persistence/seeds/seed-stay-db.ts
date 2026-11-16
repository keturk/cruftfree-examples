/**
 * Seed data for stayDb component.
 *
 * Auto-generated from .cseed seed declarations. Do not edit manually.
 */
import { MikroORM, EntityManager } from '@mikro-orm/core';
import type { AbstractSqlConnection } from '@mikro-orm/postgresql';
import { RoomType } from '../../hotel_stay_service/entities/stay_db/room-type.entity';
import { Room } from '../../hotel_stay_service/entities/stay_db/room.entity';
import { Stay } from '../../hotel_stay_service/entities/stay_db/stay.entity';

type SeedLookupValue = {
  __seedLookup: true;
  entityName: string;
  matchFields: Record<string, unknown>;
};

const ENTITY_BY_NAME = {
  RoomType,
  Room,
  Stay,
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
  tryAcquire: "SELECT pg_try_advisory_lock(hashtext(\u00272c8f5a17-e349-4d6b-91a0-3b7d6e1f8c25\u0027))",
  release: "SELECT pg_advisory_unlock(hashtext(\u00272c8f5a17-e349-4d6b-91a0-3b7d6e1f8c25\u0027))",
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
    throw new Error(`Seed component stayDb: the block lock statement returned no row.`);
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
          `Seed component stayDb: the database returned NULL for the block lock; ` +
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
        `Seed component stayDb: could not acquire the block lock after ` +
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
 * Seed stayDb component with the categories its generated profile runs.
 *
 * @param orm - MikroORM instance
 * @param profile - Deployment profile (logged; the categories were fixed at generation)
 * @param reset - Delete the rows of every table this component seeds
 *   (reverse seed order, children first) before seeding * @param anchor - The 'YYYY-MM-DD' date every relative @date / @datetime is evaluated against
 */
export async function seedStayDb(orm: MikroORM, profile: string, reset: boolean, anchor: string): Promise<void> {
  // The block's rows are written by every service that writes it: seeding holds the
  // block's session lock, so a seed never interleaves with another writer's seed of it.
  await withSessionLock(orm, () => seedStayDbLocked(orm, profile, reset, anchor));
}

async function seedStayDbLocked(orm: MikroORM, profile: string, reset: boolean, anchor: string): Promise<void> {
  const anchorDate = new Date(`${anchor}T00:00:00Z`);
  console.log(`[SeedStayDb] seed_anchor_resolved component=stayDb anchor=${anchor}`);
  const em = orm.em.fork();
  console.log(`[SeedStayDb] Seeding stayDb for profile '${profile}' reset=${reset}`);

  if (reset) {
    await em.nativeDelete(Stay, {});
    await em.nativeDelete(Room, {});
    await em.nativeDelete(RoomType, {});
    console.log(`[SeedStayDb] seed_reset_completed component=stayDb`);
  }

  // baseline data: the generated profile runs this category
  {
    // Seed RoomType (conflict on: name; an existing row is
    // left as it is)
    for (const row of baselineRowsRoomType) {
      const resolvedRow = await resolveSeedLookups(em, resolveSeedRelatives(row, anchorDate) as Record<string, unknown>);
      await em.upsert(RoomType, resolvedRow, {
        onConflictFields: ["name"],
        onConflictAction: 'ignore',
      });
    }

    // Seed Room (conflict on: number; an existing row is
    // left as it is)
    for (const row of baselineRowsRoom) {
      const resolvedRow = await resolveSeedLookups(em, resolveSeedRelatives(row, anchorDate) as Record<string, unknown>);
      await em.upsert(Room, resolvedRow, {
        onConflictFields: ["number"],
        onConflictAction: 'ignore',
      });
    }

    // Seed Stay (conflict on: code; an existing row is
    // left as it is)
    for (const row of baselineRowsStay) {
      const resolvedRow = await resolveSeedLookups(em, resolveSeedRelatives(row, anchorDate) as Record<string, unknown>);
      await em.upsert(Stay, resolvedRow, {
        onConflictFields: ["code"],
        onConflictAction: 'ignore',
      });
    }

  }

  await em.flush();
  console.log(`[SeedStayDb] Completed seeding stayDb`);
}

// baseline / RoomType
const baselineRowsRoomType = [{"id": "ad506a08-5943-5704-bf22-6862797a2726", "name": "Dune Room", "summary": "Small and quiet, looking over the marram.", "sleeps": 2, "nightlyRate": 140.0, "inventory": 4, "description": "A small room at the back of the house, with the dunes outside the window and the sea somewhere behind them.\n\nA double bed, a desk, and a shower."}, {"id": "0ffbfb63-7e4e-5da1-944d-61c90e0671d2", "name": "Tide Room", "summary": "Larger, with a view of the water.", "sleeps": 3, "nightlyRate": 195.0, "inventory": 3, "description": "On the first floor, with two windows over the water and a chair to watch it from.\n\nA king bed, a day bed, and a bath."}, {"id": "f965d088-9502-5e02-80e3-8b8fa4d326d7", "name": "The Net Loft", "summary": "The whole top floor, for a family.", "sleeps": 5, "nightlyRate": 310.0, "inventory": 2, "description": "Under the roof where the nets were once mended. **Two bedrooms**, a small kitchen and a long table."}] as readonly Record<string, unknown>[];

// baseline / Room
const baselineRowsRoom = [{"id": "46cf5f58-1743-5440-abb8-05c7b135dac9", "number": "101", "roomTypeId": "ad506a08-5943-5704-bf22-6862797a2726", "roomTypeName": "Dune Room", "floor": 1, "condition": "Ready"}, {"id": "e7e93046-167d-56f4-833d-ee4c258029d0", "number": "102", "roomTypeId": "ad506a08-5943-5704-bf22-6862797a2726", "roomTypeName": "Dune Room", "floor": 1, "condition": "Ready"}, {"id": "2617af8e-1eb2-5d4f-9896-047021b058f4", "number": "103", "roomTypeId": "ad506a08-5943-5704-bf22-6862797a2726", "roomTypeName": "Dune Room", "floor": 1, "condition": "Dirty"}, {"id": "b145d037-286b-5ba7-a1b2-f33b75693fef", "number": "104", "roomTypeId": "ad506a08-5943-5704-bf22-6862797a2726", "roomTypeName": "Dune Room", "floor": 1, "condition": "OutOfService"}, {"id": "3bfc2c40-21bb-54b3-a507-4ab9e9d29f02", "number": "201", "roomTypeId": "0ffbfb63-7e4e-5da1-944d-61c90e0671d2", "roomTypeName": "Tide Room", "floor": 2, "condition": "Ready"}, {"id": "b49fc84a-05b1-573c-9638-22b16fd056c2", "number": "202", "roomTypeId": "0ffbfb63-7e4e-5da1-944d-61c90e0671d2", "roomTypeName": "Tide Room", "floor": 2, "condition": "Ready"}, {"id": "3516dd40-8939-570c-8917-8844974afe03", "number": "203", "roomTypeId": "0ffbfb63-7e4e-5da1-944d-61c90e0671d2", "roomTypeName": "Tide Room", "floor": 2, "condition": "Ready"}, {"id": "1264b4b2-aa0a-5274-bd1a-04bb42b9c500", "number": "301", "roomTypeId": "f965d088-9502-5e02-80e3-8b8fa4d326d7", "roomTypeName": "The Net Loft", "floor": 3, "condition": "Ready"}, {"id": "453e1c90-37b1-5eae-a7f5-d8f17fd34f63", "number": "302", "roomTypeId": "f965d088-9502-5e02-80e3-8b8fa4d326d7", "roomTypeName": "The Net Loft", "floor": 3, "condition": "Ready"}] as readonly Record<string, unknown>[];

// baseline / Stay
const baselineRowsStay = [{"id": "41e1ef49-6138-5784-aa42-f1863597aefc", "code": "MH-100201", "roomTypeId": "ad506a08-5943-5704-bf22-6862797a2726", "roomTypeName": "Dune Room", "roomNumber": null, "guestId": "seed-pia", "guestName": "Pia Lund", "guestEmail": "pia@example.com", "arrival": {"__seedRelative": true, "kind": "date", "months": 0, "days": 0, "hour": 0, "minute": 0, "zone": "UTC"}, "departure": {"__seedRelative": true, "kind": "date", "months": 0, "days": 2, "hour": 0, "minute": 0, "zone": "UTC"}, "nights": 2, "guests": 2, "total": 280.0, "status": "Confirmed", "chargeId": "ch_seed_pia"}, {"id": "106be171-df0e-5249-a7e2-2f7e5e7b44cf", "code": "MH-100202", "roomTypeId": "0ffbfb63-7e4e-5da1-944d-61c90e0671d2", "roomTypeName": "Tide Room", "roomNumber": null, "guestId": "seed-noor", "guestName": "Noor Haddad", "guestEmail": "noor@example.com", "arrival": {"__seedRelative": true, "kind": "date", "months": 0, "days": 0, "hour": 0, "minute": 0, "zone": "UTC"}, "departure": {"__seedRelative": true, "kind": "date", "months": 0, "days": 3, "hour": 0, "minute": 0, "zone": "UTC"}, "nights": 3, "guests": 3, "total": 585.0, "status": "Confirmed", "chargeId": "ch_seed_noor"}, {"id": "bcb4ac73-4b2f-5a1c-aa1e-e3060a811c04", "code": "MH-100203", "roomTypeId": "0ffbfb63-7e4e-5da1-944d-61c90e0671d2", "roomTypeName": "Tide Room", "roomNumber": "201", "guestId": "seed-eli", "guestName": "Eli Marsh", "guestEmail": "eli@example.com", "arrival": {"__seedRelative": true, "kind": "date", "months": 0, "days": -2, "hour": 0, "minute": 0, "zone": "UTC"}, "departure": {"__seedRelative": true, "kind": "date", "months": 0, "days": 0, "hour": 0, "minute": 0, "zone": "UTC"}, "nights": 2, "guests": 2, "total": 390.0, "status": "CheckedIn", "chargeId": "ch_seed_eli"}, {"id": "c107e104-4e20-5c30-ad45-b2fd55df31d8", "code": "MH-100204", "roomTypeId": "f965d088-9502-5e02-80e3-8b8fa4d326d7", "roomTypeName": "The Net Loft", "roomNumber": "301", "guestId": "seed-rhys", "guestName": "Rhys Bowen", "guestEmail": "rhys@example.com", "arrival": {"__seedRelative": true, "kind": "date", "months": 0, "days": -1, "hour": 0, "minute": 0, "zone": "UTC"}, "departure": {"__seedRelative": true, "kind": "date", "months": 0, "days": 4, "hour": 0, "minute": 0, "zone": "UTC"}, "nights": 5, "guests": 5, "total": 1550.0, "status": "CheckedIn", "chargeId": "ch_seed_rhys"}, {"id": "0afc6b47-6057-5d01-978b-3dcb451abf59", "code": "MH-100205", "roomTypeId": "ad506a08-5943-5704-bf22-6862797a2726", "roomTypeName": "Dune Room", "roomNumber": null, "guestId": "seed-tova", "guestName": "Tova Stein", "guestEmail": "tova@example.com", "arrival": {"__seedRelative": true, "kind": "date", "months": 0, "days": 1, "hour": 0, "minute": 0, "zone": "UTC"}, "departure": {"__seedRelative": true, "kind": "date", "months": 0, "days": 3, "hour": 0, "minute": 0, "zone": "UTC"}, "nights": 2, "guests": 1, "total": 280.0, "status": "Confirmed", "chargeId": "ch_seed_tova"}, {"id": "cb768b27-9f92-5281-85c5-ae1c889c08ee", "code": "MH-100206", "roomTypeId": "ad506a08-5943-5704-bf22-6862797a2726", "roomTypeName": "Dune Room", "roomNumber": "103", "guestId": "seed-ivo", "guestName": "Ivo Petrov", "guestEmail": "ivo@example.com", "arrival": {"__seedRelative": true, "kind": "date", "months": 0, "days": -3, "hour": 0, "minute": 0, "zone": "UTC"}, "departure": {"__seedRelative": true, "kind": "date", "months": 0, "days": -1, "hour": 0, "minute": 0, "zone": "UTC"}, "nights": 2, "guests": 2, "total": 280.0, "status": "CheckedOut", "chargeId": "ch_seed_ivo"}] as readonly Record<string, unknown>[];

