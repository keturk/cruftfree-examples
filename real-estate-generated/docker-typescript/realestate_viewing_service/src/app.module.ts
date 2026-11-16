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
import { MetricsController } from './observability/metrics.controller';
import { HealthController } from './observability/health.controller';
import { BuyerViewingAPIController } from './controllers/buyer_viewing_api.controller';
import { AgentViewingAPIController } from './controllers/agent_viewing_api.controller';
import { ViewingService } from './services/viewing.service';
import { APP_INTERCEPTOR } from '@nestjs/core';
import { MetricsInterceptor } from './observability/metrics.interceptor';
import { JsonScalarResponseInterceptor } from './common/json-scalar-response.interceptor';
import { LoggerModule } from './observability/logger.module';
import { getThrottlerModule } from './realestate_viewing_service/gateway-throttler.config';
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
    getThrottlerModule(),
    LoggerModule,
    JobsModule,
    BlockConsumerModule,
    HttpClientsModule,
  ],
  controllers: [
    MetricsController,
    HealthController,
    RuntimeReadinessController,
    BuyerViewingAPIController,
    AgentViewingAPIController,
  ],
  providers: [
    { provide: RemoteConfigClient, useFactory: sharedConfigClient },
    { provide: APP_FILTER, useClass: AllExceptionsFilter },
    { provide: APP_INTERCEPTOR, useClass: JsonScalarResponseInterceptor },
    { provide: APP_INTERCEPTOR, useClass: MetricsInterceptor },
    ViewingService,
    FunctionsService,
  ],
})
export class AppModule {
}
