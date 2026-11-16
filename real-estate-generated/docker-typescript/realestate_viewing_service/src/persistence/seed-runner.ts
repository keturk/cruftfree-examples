/**
 * Seed runner for realestate.ViewingService.
 *
 * Usage: node dist/persistence/seed-runner.js [--profile <name>] [--reset]
 * Seeds the categories the profile this service was generated for runs; --profile
 * names that profile and any other value is refused.
 * --reset deletes what every component seeds before seeding: the rows of each
 * RDBMS table (children first), every document of each MongoDB collection, each
 * seeded DynamoDB item and each existing seed target object.
 * --anchor YYYY-MM-DD is the date every relative @date / @datetime is evaluated
 * against (default: today, UTC); the same anchor gives the same rows.
 * The runner starts the service's own application context once and takes every
 * connection from it; it resolves no connection or credential itself.
 * Any failure exits with status 1.
 *
 * Auto-generated from .cseed seed declarations. Do not edit manually.
 */
import { NestFactory } from '@nestjs/core';
import type { INestApplicationContext } from '@nestjs/common';
import { AppModule } from '../app.module';
import { assembleSettings } from '../config/settings';
import { MikroORM } from '@mikro-orm/core';
import { seedViewingDb } from './seeds/seed-viewing-db';

/** The profile this service was generated for (the deployment's resolved profile). */
export const GENERATED_PROFILE = 'test';

const PROFILE_FLAG = '--profile';
const RESET_FLAG = '--reset';
const ANCHOR_FLAG = '--anchor';
const ISO_DATE = /^(\d{4})-(\d{2})-(\d{2})$/;

/** The anchor as 'YYYY-MM-DD'; throws unless it is a real calendar date. */
function requireAnchorDate(text: string): string {
  const match = ISO_DATE.exec(text);
  const real =
    match !== null &&
    new Date(Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3]))).toISOString().slice(0, 10) === text;
  if (!real) {
    throw new Error(`${ANCHOR_FLAG} needs a calendar date as YYYY-MM-DD, e.g. ${ANCHOR_FLAG} 2026-01-31.`);
  }
  return text;
}

/**
 * Why --reset cannot run: one entry per component that seeds an appendOnly table,
 * whose rows the database refuses to delete. A reset is refused before any
 * component deletes a row.
 */
const RESET_REFUSALS: readonly string[] = [];

/** The profile when it is GENERATED_PROFILE; this runner seeds no other profile. */
function requireGeneratedProfile(profile: string): string {
  if (profile !== GENERATED_PROFILE) {
    throw new Error(
      `This seed runner was generated for profile '${GENERATED_PROFILE}' and runs the categories ` +
        `that profile runs; profile '${profile}' is refused. Generate the service for '${profile}' instead.`,
    );
  }
  return profile;
}

export async function runSeeds(app: INestApplicationContext, profile: string, reset: boolean, anchor?: string): Promise<void> {
  requireGeneratedProfile(profile);
  if (reset && RESET_REFUSALS.length > 0) {
    throw new Error(RESET_REFUSALS.join('\n'));
  }
  console.log(`[SeedRunner] seed_started service=realestate.ViewingService profile=${profile} reset=${reset}`);
  const anchorDate = anchor !== undefined ? requireAnchorDate(anchor) : new Date().toISOString().slice(0, 10);
  await seedViewingDb(app.get<MikroORM>(MikroORM), profile, reset, anchorDate);
  console.log(`[SeedRunner] seed_completed service=realestate.ViewingService profile=${profile}`);
}

export interface SeedArgs {
  readonly profile: string;
  readonly reset: boolean;
  readonly anchor?: string;
}

/** Parse --profile <name> / --reset / --anchor <date>; an unknown flag or a --profile without a value throws. */
export function parseSeedArgs(argv: ReadonlyArray<string>): SeedArgs {
  let profile = GENERATED_PROFILE;
  let reset = false;
  let anchor: string | undefined;
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === RESET_FLAG) {
      reset = true;
      continue;
    }
    if (arg === ANCHOR_FLAG) {
      const value = argv[index + 1];
      if (value === undefined) {
        throw new Error(`${ANCHOR_FLAG} needs a date, e.g. ${ANCHOR_FLAG} 2026-01-31.`);
      }
      anchor = requireAnchorDate(value);
      index += 1;
      continue;
    }
    if (arg === PROFILE_FLAG) {
      const value = argv[index + 1];
      if (value === undefined || value.startsWith('--') || value.trim() === '') {
        throw new Error(
          `${PROFILE_FLAG} needs a profile name, e.g. ${PROFILE_FLAG} ${GENERATED_PROFILE}. ` +
            `Omit it to seed for the generated profile '${GENERATED_PROFILE}'.`,
        );
      }
      if (value !== GENERATED_PROFILE) {
        throw new Error(
          `This seed runner was generated for profile '${GENERATED_PROFILE}' and runs the categories ` +
            `that profile runs; ${PROFILE_FLAG} '${value}' is refused. Generate the service for '${value}' instead.`,
        );
      }
      profile = value;
      index += 1;
      continue;
    }
    throw new Error(
      `Unknown seed runner argument '${arg}'. Valid flags: ${PROFILE_FLAG} <name>, ${RESET_FLAG}, ${ANCHOR_FLAG} <date>. ` +
        `Usage: node dist/persistence/seed-runner.js [${PROFILE_FLAG} <name>] [${RESET_FLAG}] [${ANCHOR_FLAG} <date>]`,
    );
  }
  return { profile, reset, anchor };
}

async function main(): Promise<void> {
  const args = parseSeedArgs(process.argv.slice(2));
  // Assemble the application settings before the application module is built, as main.ts
  // does: a provider whose factory reads a setting while the module is constructed (the
  // rate limiter's Redis client) would otherwise run before the assembly has finished.
  await assembleSettings();
  const app = await NestFactory.createApplicationContext(AppModule, { logger: ['error', 'warn'] });
  try {
    await runSeeds(app, args.profile, args.reset, args.anchor);
  } finally {
    await app.close();
  }
}

if (require.main === module) {
  main()
    .then(() => process.exit(0))
    .catch((err: unknown) => {
      console.error(`[SeedRunner] seed_failed service=realestate.ViewingService error=${err instanceof Error ? err.message : String(err)}`);
      process.exit(1);
    });
}
