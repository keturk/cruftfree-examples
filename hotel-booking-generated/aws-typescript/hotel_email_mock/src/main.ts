import './observability/tracing';
import { NestFactory } from '@nestjs/core';
import type { NestExpressApplication } from '@nestjs/platform-express';
import { ValidationPipe } from '@nestjs/common';
import type { ValidationError } from 'class-validator';
import { bodyParseErrorMiddleware, bodyValidationException } from './common/request-validation';
import { EntityManager } from '@mikro-orm/core';
import { loadIdentityPlanAtStartup } from './auth/identity';
import { bindApiKeyStoreEntityManager } from './auth/api-key-verify';
import { AppModule } from './app.module';
import { requestContextMiddleware } from './hotel_email_mock/_requestContext';
import { hostCheckMiddleware } from "./common/host-check";
import { CORS_POLICY } from "./common/cors-policy";
import { wireJsonReplacer } from "./common/wire-json";
import { SwaggerModule, DocumentBuilder } from '@nestjs/swagger';
import { assembleSettings } from './config/settings';
import { MikroORM } from '@mikro-orm/core';
import type { AbstractSqlConnection } from '@mikro-orm/postgresql';
import { GENERATED_PROFILE, runSeeds } from './persistence/seed-runner';
import { sharedConfigClient } from './config/remoteConfig';
import { Delivery } from './dto/delivery.struct';
import { SendEmailRequest } from './dto/send-email-request.struct';
import { ApiKeyVerifyRequest } from './dto/api-key-verify-request.struct';

/**
 * Write an error message to stderr and exit. Uses process.stderr.write()
 * with a callback to ensure the message is flushed to the Docker log driver
 * before process.exit() terminates the event loop. In non-TTY mode (Docker
 * detached containers), console.error() is block-buffered and process.exit()
 * kills the process before the buffer flushes — losing the error message.
 */
function fatal(label: string, err: unknown): void {
  const msg = err instanceof Error ? err.stack ?? err.message : String(err);
  process.stderr.write(`${label}: ${msg}\n`, () => process.exit(1));
  setTimeout(() => process.exit(1), 1000).unref();
}

// Process-level error handlers — ensure crashes are always logged,
// even when they bypass bootstrap().catch().
process.on('uncaughtException', (err) => fatal('FATAL uncaughtException', err));
process.on('unhandledRejection', (reason) => fatal('FATAL unhandledRejection', reason));
process.on('exit', (code) => {
  console.error(`Process exit code=${code} rss=${Math.round(process.memoryUsage().rss / 1024 / 1024)}MB`);
});

// How long a platform stop may take before the process exits regardless. It stays inside the
// shortest stop grace a platform gives a container, so the process exits by its own hand.
const SHUTDOWN_DEADLINE_MS = 8000;

// The running application, once created: a stop before that has nothing to close.
let application: NestExpressApplication | undefined;
let stopping = false;

process.on('SIGTERM', () => {
  if (stopping) {
    return;
  }
  stopping = true;
  // The process's one config-store client was started by the settings assembly;
  // stopping it tears its background poll timer down cleanly.
  sharedConfigClient().stop();
  process.stderr.write('Received SIGTERM\n');
  setTimeout(() => process.exit(143), SHUTDOWN_DEADLINE_MS).unref();
  // Closing runs every provider's shutdown hook: consumers settle their in-flight message and
  // stop, in-process runtimes stop, and cache and database clients close.
  const closed = application === undefined ? Promise.resolve() : application.close();
  closed.then(
    () => process.exit(143),
    (err: unknown) => {
      const msg = err instanceof Error ? err.stack ?? err.message : String(err);
      process.stderr.write(`Application failed to stop: ${msg}\n`, () => process.exit(143));
    },
  );
});

/** The startup seed lock's statements, spelled by the database's dialect, and its wait budget. */
const SESSION_LOCK = {
  tryAcquire: "SELECT pg_try_advisory_lock(hashtext(\u0027hotel.EmailMock:__cruftfree_startup_seed__\u0027))",
  release: "SELECT pg_advisory_unlock(hashtext(\u0027hotel.EmailMock:__cruftfree_startup_seed__\u0027))",
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
    throw new Error(`Service hotel.EmailMock: the startup seed lock statement returned no row.`);
  }
  return Object.values(first as Record<string, unknown>)[0];
}

/**
 * Runs *work* holding the startup seed lock on a dedicated connection of *orm*: a bounded
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
          `Service hotel.EmailMock: the database returned NULL for the startup seed lock; ` +
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
        `Service hotel.EmailMock: could not acquire the startup seed lock after ` +
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
        console.warn(`session_unlock_failed lock=startup seed error=${String(error)}`);
      }
    }
  } finally {
    knex.client.releaseConnection(lockConnection);
  }
}


async function bootstrap() {
  // Assemble the application settings -- the config store's connection facts and the
  // deploy-time application settings -- before anything reads one. A key or setting the
  // deployment did not supply aborts startup here, naming it, instead of failing at
  // first use. This also starts the process's one config-store client, whose feature
  // flags and tuning values are therefore available to every request handler (it honors
  // failOpen: a failed initial refresh falls back to generated defaults when failOpen is
  // true and aborts startup when it is false).
  await assembleSettings();
  // Load the identity provider plan before anything serves: a missing,
  // unreadable or unsupported plan aborts startup here instead of turning
  // every authenticated request into a 401.
  loadIdentityPlanAtStartup();
  const app = await NestFactory.create<NestExpressApplication>(AppModule, { rawBody: true });
  application = app;

  // Every JSON answer is written by express's `res.json`, so this is where a route's
  // `Bytes` value takes its declared JSON form.
  app.set('json replacer', wireJsonReplacer);

  // Ambient request context (Request.* accessors reached from service
  // functions). Registered first, so it is the OUTERMOST layer: the binding
  // exists before any other middleware, guard, or handler runs on the request.
  app.use(requestContextMiddleware);

  // Host-header check: a request whose Host is not allowed is refused here, before
  // any CORS answer, guard or route. The WebSocket upgrade router applies the same check.
  app.use(hostCheckMiddleware);

  // Bind, per API-key provider this service stores, the EntityManager of the
  // block holding its keys and -- when a per-key rate limit is mapped -- the
  // Redis client of its rate-limit cache, so the verify route and in-process
  // key resolution share one verification path.
  bindApiKeyStoreEntityManager("emailKeys", app.get(EntityManager));

  // Configure Swagger/OpenAPI documentation
  const config = new DocumentBuilder()
    .setTitle("hotel.EmailMock API")
    .setDescription('Auto-generated API documentation for hotel.EmailMock')
    .setVersion('1.0')
    .addBearerAuth()
    .addApiKey({ type: 'apiKey', in: 'header', name: "X-Email-Api-Key" }, "emailKeys")
    .build();
  const document = SwaggerModule.createDocument(app, config, {
    extraModels: [Delivery, SendEmailRequest, ApiKeyVerifyRequest],
  });
  SwaggerModule.setup('docs', app, document, {
    jsonDocumentUrl: '/openapi.json',
  });

  // Request bodies reach validation exactly as sent, and responses leave as
  // the handler returned them: a field is spelled by its camelCase wire name
  // on both legs, and no key is rewritten in either direction. The pipe below
  // rejects any other spelling of a declared field as an unknown property.

  // A custom exceptionFactory replaces NestJS's default (which flattens each
  // ValidationError into a plain message string, discarding the structured
  // property/children tree): the request refusal is built here, from the
  // validator's own tree, as `(location, field, code)` entries naming the
  // request's actual property path -- never the framework's own messages,
  // which embed fragments of the received value. `validateCustomDecorators`
  // makes the pipe validate the `@RequestBody(...)` parameter like `@Body()`.
  app.useGlobalPipes(new ValidationPipe({
    whitelist: true,
    forbidNonWhitelisted: true,
    transform: true,
    validateCustomDecorators: true,
    exceptionFactory: (errors: ValidationError[]) => bodyValidationException(errors),
  }));

  // CORS: a cross-origin request is answered only for the declared origins, methods
  // and headers (httpSecurity), with credentials.
  app.enableCors(CORS_POLICY);
  // Routes and body parsers register during init. A body the parser could not
  // parse never reaches a route, so the registered error middleware answers it
  // (an Express error handler runs after the layers it follows).
  await app.init();
  // Seed before anything serves, from the service's own application context, under the
  // seed lock.
  await withSessionLock(
    app.get<MikroORM>(MikroORM),
    () => runSeeds(app, GENERATED_PROFILE, false),
  );
  app.getHttpAdapter().getInstance().use(bodyParseErrorMiddleware);
  // The port is the service's declared port, baked at generation: the platform's port mapping
  // and health probes are generated from the same declaration.
  await app.listen(8091);
}
bootstrap().catch((err) => fatal('Application failed to start', err));
