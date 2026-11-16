/**
 * Seed runner for realestate.DealService.
 *
 * Usage: node dist/persistence/seed-runner.js [--profile <name>] [--reset]
 * Seeds the categories the profile this service was generated for runs; --profile
 * names that profile and any other value is refused.
 * --reset deletes what every component seeds before seeding: the rows of each
 * RDBMS table (children first), every document of each MongoDB collection, each
 * seeded DynamoDB item and each existing seed target object.
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
import { seedDealDb } from './seeds/seed-deal-db';

/** The profile this service was generated for (the deployment's resolved profile). */
export const GENERATED_PROFILE = 'development';

const PROFILE_FLAG = '--profile';
const RESET_FLAG = '--reset';

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

export async function runSeeds(app: INestApplicationContext, profile: string, reset: boolean): Promise<void> {
  requireGeneratedProfile(profile);
  if (reset && RESET_REFUSALS.length > 0) {
    throw new Error(RESET_REFUSALS.join('\n'));
  }
  console.log(`[SeedRunner] seed_started service=realestate.DealService profile=${profile} reset=${reset}`);
  await seedDealDb(app.get<MikroORM>(MikroORM), profile, reset);
  console.log(`[SeedRunner] seed_completed service=realestate.DealService profile=${profile}`);
}

export interface SeedArgs {
  readonly profile: string;
  readonly reset: boolean;
}

/** Parse --profile <name> / --reset; an unknown flag or a --profile without a value throws. */
export function parseSeedArgs(argv: ReadonlyArray<string>): SeedArgs {
  let profile = GENERATED_PROFILE;
  let reset = false;
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === RESET_FLAG) {
      reset = true;
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
      `Unknown seed runner argument '${arg}'. Valid flags: ${PROFILE_FLAG} <name>, ${RESET_FLAG}. ` +
        `Usage: node dist/persistence/seed-runner.js [${PROFILE_FLAG} <name>] [${RESET_FLAG}]`,
    );
  }
  return { profile, reset };
}

async function main(): Promise<void> {
  const args = parseSeedArgs(process.argv.slice(2));
  // Assemble the application settings before the application module is built, as main.ts
  // does: a provider whose factory reads a setting while the module is constructed (the
  // rate limiter's Redis client) would otherwise run before the assembly has finished.
  await assembleSettings();
  const app = await NestFactory.createApplicationContext(AppModule, { logger: ['error', 'warn'] });
  try {
    await runSeeds(app, args.profile, args.reset);
  } finally {
    await app.close();
  }
}

if (require.main === module) {
  main()
    .then(() => process.exit(0))
    .catch((err: unknown) => {
      console.error(`[SeedRunner] seed_failed service=realestate.DealService error=${err instanceof Error ? err.message : String(err)}`);
      process.exit(1);
    });
}
