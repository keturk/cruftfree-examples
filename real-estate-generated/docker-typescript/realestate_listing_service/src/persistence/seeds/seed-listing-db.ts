/**
 * Seed data for listingDb component.
 *
 * Auto-generated from .cseed seed declarations. Do not edit manually.
 */
import { MikroORM, EntityManager } from '@mikro-orm/core';
import type { AbstractSqlConnection } from '@mikro-orm/postgresql';
import { Neighbourhood } from '../../realestate_listing_service/entities/listing_db/neighbourhood.entity';
import { Listing } from '../../realestate_listing_service/entities/listing_db/listing.entity';
import { PriceChange } from '../../realestate_listing_service/entities/listing_db/price-change.entity';

type SeedLookupValue = {
  __seedLookup: true;
  entityName: string;
  matchFields: Record<string, unknown>;
};

const ENTITY_BY_NAME = {
  Neighbourhood,
  Listing,
  PriceChange,
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
  tryAcquire: "SELECT pg_try_advisory_lock(hashtext(\u0027006bfb76-6012-4878-9e8a-06fd9636de60\u0027))",
  release: "SELECT pg_advisory_unlock(hashtext(\u0027006bfb76-6012-4878-9e8a-06fd9636de60\u0027))",
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
    throw new Error(`Seed component listingDb: the block lock statement returned no row.`);
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
          `Seed component listingDb: the database returned NULL for the block lock; ` +
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
        `Seed component listingDb: could not acquire the block lock after ` +
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
 * Seed listingDb component with the categories its generated profile runs.
 *
 * @param orm - MikroORM instance
 * @param profile - Deployment profile (logged; the categories were fixed at generation)
 * @param reset - Delete the rows of every table this component seeds
 *   (reverse seed order, children first) before seeding; refused,
 *   because an appendOnly table of this component refuses deletes * @param anchor - The 'YYYY-MM-DD' date every relative @date / @datetime is evaluated against
 */
export async function seedListingDb(orm: MikroORM, profile: string, reset: boolean, anchor: string): Promise<void> {
  if (reset) {
    // A table this component seeds refuses every DELETE (appendOnly): the reset is
    // refused before any row is deleted, never narrowed to the other tables.
    throw new Error("Seed reset refused for component \u0027listingDb\u0027: the table of appendOnly entity PriceChange refuses every DELETE, so --reset cannot empty them, and no row was deleted. Seed without --reset.");
  }
  // The block's rows are written by every service that writes it: seeding holds the
  // block's session lock, so a seed never interleaves with another writer's seed of it.
  await withSessionLock(orm, () => seedListingDbLocked(orm, profile, reset, anchor));
}

async function seedListingDbLocked(orm: MikroORM, profile: string, reset: boolean, anchor: string): Promise<void> {
  const anchorDate = new Date(`${anchor}T00:00:00Z`);
  console.log(`[SeedListingDb] seed_anchor_resolved component=listingDb anchor=${anchor}`);
  const em = orm.em.fork();
  console.log(`[SeedListingDb] Seeding listingDb for profile '${profile}' reset=${reset}`);

  if (reset) {
    await em.nativeDelete(PriceChange, {});
    await em.nativeDelete(Listing, {});
    await em.nativeDelete(Neighbourhood, {});
    console.log(`[SeedListingDb] seed_reset_completed component=listingDb`);
  }

  // baseline data: the generated profile runs this category
  {
    // Seed Neighbourhood (conflict on: name; an existing row is
    // left as it is)
    for (const row of baselineRowsNeighbourhood) {
      const resolvedRow = await resolveSeedLookups(em, resolveSeedRelatives(row, anchorDate) as Record<string, unknown>);
      await em.upsert(Neighbourhood, resolvedRow, {
        onConflictFields: ["name"],
        onConflictAction: 'ignore',
      });
    }

    // Seed Listing (conflict on: id; an existing row is
    // left as it is)
    for (const row of baselineRowsListing) {
      const resolvedRow = await resolveSeedLookups(em, resolveSeedRelatives(row, anchorDate) as Record<string, unknown>);
      await em.upsert(Listing, resolvedRow, {
        onConflictFields: ["id"],
        onConflictAction: 'ignore',
      });
    }

    // Seed PriceChange (conflict on: id; an existing row is
    // left as it is)
    for (const row of baselineRowsPriceChange) {
      const resolvedRow = await resolveSeedLookups(em, resolveSeedRelatives(row, anchorDate) as Record<string, unknown>);
      await em.upsert(PriceChange, resolvedRow, {
        onConflictFields: ["id"],
        onConflictAction: 'ignore',
      });
    }

  }

  await em.flush();
  console.log(`[SeedListingDb] Completed seeding listingDb`);
}

// baseline / Neighbourhood
const baselineRowsNeighbourhood = [{"id": "b16b7f40-a988-5aec-8a1b-4d167b25af27", "name": "Pearl District", "city": "Portland", "latitude": 45.529, "longitude": -122.682}, {"id": "15b495ea-7174-5af5-8db0-c94e9e2d4a0f", "name": "Alberta Arts", "city": "Portland", "latitude": 45.559, "longitude": -122.646}, {"id": "71ec760a-6b96-5c63-b353-896a935e5916", "name": "Sellwood", "city": "Portland", "latitude": 45.465, "longitude": -122.655}, {"id": "a35d51ce-ce1d-5295-8095-e7cbbfd5c633", "name": "West Hills", "city": "Portland", "latitude": 45.512, "longitude": -122.712}] as readonly Record<string, unknown>[];

// baseline / Listing
const baselineRowsListing = [{"id": "db431b5b-cc77-532b-a3fe-c824802832b4", "title": "Loft over the old mill", "neighbourhoodName": "Pearl District", "city": "Portland", "kind": "Apartment", "price": 625000.0, "bedrooms": 2, "bathrooms": 2, "areaSqm": 118, "status": "Active", "agentName": "Dana Whitlock", "agentEmail": "dana@cobblestone.example.com", "publishedAt": {"__seedRelative": true, "kind": "datetime", "months": 0, "days": -6, "hour": 10, "minute": 0, "zone": "UTC"}, "latitude": 45.53, "longitude": -122.684, "summary": "Brick walls and tall windows on the fourth floor, two minutes from the streetcar. The kitchen faces the morning sun."}, {"id": "618dd1a8-4d40-5d45-9e8a-5ad3059cdb15", "title": "Rose Street bungalow", "neighbourhoodName": "Alberta Arts", "city": "Portland", "kind": "House", "price": 549000.0, "bedrooms": 3, "bathrooms": 2, "areaSqm": 142, "status": "Active", "agentName": "Dana Whitlock", "agentEmail": "dana@cobblestone.example.com", "publishedAt": {"__seedRelative": true, "kind": "datetime", "months": 0, "days": -4, "hour": 9, "minute": 30, "zone": "UTC"}, "latitude": 45.557, "longitude": -122.649, "summary": "A 1924 bungalow with its original fir floors, a deep front porch and a garden that has been looked after for thirty years."}, {"id": "c721aaec-b1c1-5f5f-be9d-f85426e2f14f", "title": "End of the terrace", "neighbourhoodName": "Alberta Arts", "city": "Portland", "kind": "Townhouse", "price": 479000.0, "bedrooms": 3, "bathrooms": 3, "areaSqm": 131, "status": "Active", "agentName": "Dana Whitlock", "agentEmail": "dana@cobblestone.example.com", "publishedAt": {"__seedRelative": true, "kind": "datetime", "months": 0, "days": -2, "hour": 11, "minute": 0, "zone": "UTC"}, "latitude": 45.561, "longitude": -122.642, "summary": "The end house of a new row, with a rooftop deck, a garage and solar panels already paying for themselves."}, {"id": "641b3123-ef89-5e76-9a88-89bf705a085c", "title": "Riverside cottage", "neighbourhoodName": "Sellwood", "city": "Portland", "kind": "Cottage", "price": 415000.0, "bedrooms": 2, "bathrooms": 1, "areaSqm": 78, "status": "Active", "agentName": "Noor Bellamy", "agentEmail": "noor@cobblestone.example.com", "publishedAt": {"__seedRelative": true, "kind": "datetime", "months": 0, "days": -9, "hour": 14, "minute": 0, "zone": "UTC"}, "latitude": 45.463, "longitude": -122.661, "summary": "Small and bright, one street from the river path. The garden backs onto the park and there is room for a studio."}, {"id": "8c6ef7d4-e6b4-5bfe-a736-9d4f04f40b33", "title": "Oak Lane family home", "neighbourhoodName": "West Hills", "city": "Portland", "kind": "House", "price": 1150000.0, "bedrooms": 5, "bathrooms": 4, "areaSqm": 320, "status": "Active", "agentName": "Noor Bellamy", "agentEmail": "noor@cobblestone.example.com", "publishedAt": {"__seedRelative": true, "kind": "datetime", "months": 0, "days": -12, "hour": 10, "minute": 0, "zone": "UTC"}, "latitude": 45.514, "longitude": -122.716, "summary": "Five bedrooms among old oaks, with a view of the mountain from the upstairs landing and a garden on three levels."}, {"id": "09f4cfa3-aad1-5ef8-b199-c95af0e26824", "title": "Hillside building plot", "neighbourhoodName": "West Hills", "city": "Portland", "kind": "Land", "price": 289000.0, "bedrooms": 0, "bathrooms": 0, "areaSqm": 900, "status": "Active", "agentName": "Noor Bellamy", "agentEmail": "noor@cobblestone.example.com", "publishedAt": {"__seedRelative": true, "kind": "datetime", "months": 0, "days": -1, "hour": 16, "minute": 0, "zone": "UTC"}, "latitude": 45.509, "longitude": -122.721, "summary": "A south-facing plot with services at the road and permission for one house. The neighbours have built well."}, {"id": "292e8ca5-bd47-5498-a9a6-d0432271b4a1", "title": "Corner flat, coming soon", "neighbourhoodName": "Sellwood", "city": "Portland", "kind": "Apartment", "price": 365000.0, "bedrooms": 1, "bathrooms": 1, "areaSqm": 61, "status": "Draft", "agentName": "Dana Whitlock", "agentEmail": "dana@cobblestone.example.com", "publishedAt": null, "latitude": 45.468, "longitude": -122.652, "summary": "Still being photographed."}] as readonly Record<string, unknown>[];

// baseline / PriceChange
const baselineRowsPriceChange = [{"id": "5a7df384-ae9d-514c-b41f-014d2e579a0f", "listingId": "8c6ef7d4-e6b4-5bfe-a736-9d4f04f40b33", "oldPrice": 1225000.0, "newPrice": 1150000.0}] as readonly Record<string, unknown>[];

