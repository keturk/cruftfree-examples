import { Module } from '@nestjs/common';
import { APP_GUARD, APP_FILTER } from '@nestjs/core';
import { SecretsModule } from './realestate_listing_service/secrets';
import { SettingsModule } from './config/settings';
import { RemoteConfigClient, sharedConfigClient } from './config/remoteConfig';
import { RuntimeReadinessController } from './config/runtime-readiness.controller';
import { MikroOrmModule } from '@mikro-orm/nestjs';
import { Neighbourhood } from './realestate_listing_service/entities/listing_db/neighbourhood.entity';
import { Listing } from './realestate_listing_service/entities/listing_db/listing.entity';
import { PriceChange } from './realestate_listing_service/entities/listing_db/price-change.entity';
import { ListingDbDatabaseModule } from './listing-db/database.module';
import { PubsubModule as PubsubInst1 } from './mq/pubsub.module';
import { HealthController } from './observability/health.controller';
import { PubsubHealthService as MqPubsubHealth } from './mq/pubsub.health';
import { HomesAPIController } from './controllers/homes_api.controller';
import { AgentListingAPIController } from './controllers/agent_listing_api.controller';
import { ListingInternalAPIController } from './controllers/listing_internal_api.controller';
import { NeighbourhoodService } from './services/neighbourhood.service';
import { ListingService } from './services/listing.service';
import { PriceChangeService } from './services/price_change.service';
import { APP_INTERCEPTOR } from '@nestjs/core';
import { JsonScalarResponseInterceptor } from './common/json-scalar-response.interceptor';
import { LoggerModule } from './observability/logger.module';
import { TrustedCallerGuard } from './auth/trusted-caller.guard';
import { AllExceptionsFilter } from './errors/all-exceptions-filter';
import { FunctionsService } from './functions';

@Module({
  imports: [
    SettingsModule,
    SecretsModule,
    ListingDbDatabaseModule,
    MikroOrmModule.forFeature([
      Neighbourhood,
      Listing,
      PriceChange,
    ]),
    PubsubInst1,
    LoggerModule,
  ],
  controllers: [
    HealthController,
    RuntimeReadinessController,
    HomesAPIController,
    AgentListingAPIController,
    ListingInternalAPIController,
  ],
  providers: [
    { provide: RemoteConfigClient, useFactory: sharedConfigClient },
    { provide: APP_GUARD, useClass: TrustedCallerGuard },
    { provide: APP_FILTER, useClass: AllExceptionsFilter },
    { provide: APP_INTERCEPTOR, useClass: JsonScalarResponseInterceptor },
    MqPubsubHealth,
    NeighbourhoodService,
    ListingService,
    PriceChangeService,
    FunctionsService,
  ],
})
export class AppModule {
}
