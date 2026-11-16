import { Module } from '@nestjs/common';
import { APP_GUARD, APP_FILTER } from '@nestjs/core';
import { SecretsModule } from './realestate_viewing_service/secrets';
import { SettingsModule } from './config/settings';
import { RemoteConfigClient, sharedConfigClient } from './config/remoteConfig';
import { RuntimeReadinessController } from './config/runtime-readiness.controller';
import { MikroOrmModule } from '@mikro-orm/nestjs';
import { Viewing } from './realestate_viewing_service/entities/viewing_db/viewing.entity';
import { ViewingDbDatabaseModule } from './viewing-db/database.module';
import { PubsubModule as PubsubInst1 } from './mq/pubsub.module';
import { CqrsModule } from '@nestjs/cqrs';
import { HealthController } from './observability/health.controller';
import { BuyerViewingAPIController } from './controllers/buyer_viewing_api.controller';
import { AgentViewingAPIController } from './controllers/agent_viewing_api.controller';
import { ViewingService } from './services/viewing.service';
import { APP_INTERCEPTOR } from '@nestjs/core';
import { JsonScalarResponseInterceptor } from './common/json-scalar-response.interceptor';
import { LoggerModule } from './observability/logger.module';
import { TrustedCallerGuard } from './auth/trusted-caller.guard';
import { JobsModule } from './jobs/jobs.module';
import { BlockConsumerModule } from "./messaging/block-consumer-host.service";
import { HttpClientsModule } from './http-clients.module';
import { AllExceptionsFilter } from './errors/all-exceptions-filter';
import { FunctionsService } from './functions';

@Module({
  imports: [
    SettingsModule,
    SecretsModule,
    ViewingDbDatabaseModule,
    MikroOrmModule.forFeature([
      Viewing,
    ]),
    PubsubInst1,
    CqrsModule.forRoot(),
    LoggerModule,
    JobsModule,
    BlockConsumerModule,
    HttpClientsModule,
  ],
  controllers: [
    HealthController,
    RuntimeReadinessController,
    BuyerViewingAPIController,
    AgentViewingAPIController,
  ],
  providers: [
    { provide: RemoteConfigClient, useFactory: sharedConfigClient },
    { provide: APP_GUARD, useClass: TrustedCallerGuard },
    { provide: APP_FILTER, useClass: AllExceptionsFilter },
    { provide: APP_INTERCEPTOR, useClass: JsonScalarResponseInterceptor },
    ViewingService,
    FunctionsService,
  ],
})
export class AppModule {
}
