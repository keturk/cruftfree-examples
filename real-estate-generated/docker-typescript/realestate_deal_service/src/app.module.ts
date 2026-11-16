import { Module } from '@nestjs/common';
import { APP_GUARD, APP_FILTER } from '@nestjs/core';
import { SecretsModule } from './realestate_deal_service/secrets';
import { SettingsModule } from './config/settings';
import { RemoteConfigClient, sharedConfigClient } from './config/remoteConfig';
import { RuntimeReadinessController } from './config/runtime-readiness.controller';
import { MikroOrmModule } from '@mikro-orm/nestjs';
import { Offer } from './realestate_deal_service/entities/deal_db/offer.entity';
import { Contract } from './realestate_deal_service/entities/deal_db/contract.entity';
import { DealDbDatabaseModule } from './deal-db/database.module';
import { MetricsController } from './observability/metrics.controller';
import { HealthController } from './observability/health.controller';
import { BuyerDealAPIController } from './controllers/buyer_deal_api.controller';
import { AgentDealAPIController } from './controllers/agent_deal_api.controller';
import { OfferService } from './services/offer.service';
import { ContractService } from './services/contract.service';
import { APP_INTERCEPTOR } from '@nestjs/core';
import { MetricsInterceptor } from './observability/metrics.interceptor';
import { JsonScalarResponseInterceptor } from './common/json-scalar-response.interceptor';
import { LoggerModule } from './observability/logger.module';
import { GatewayJwtVerifyController } from './realestate_deal_service/gateway-jwt-verify.controller';
import { getThrottlerModule } from './realestate_deal_service/gateway-throttler.config';
import { JobsModule } from './jobs/jobs.module';
import { HttpClientsModule } from './http-clients.module';
import { AllExceptionsFilter } from './errors/all-exceptions-filter';
import { FunctionsService } from './functions';

@Module({
  imports: [
    SettingsModule,
    SecretsModule,
    DealDbDatabaseModule,
    MikroOrmModule.forFeature([
      Offer,
      Contract,
    ]),
    getThrottlerModule(),
    LoggerModule,
    JobsModule,
    HttpClientsModule,
  ],
  controllers: [
    MetricsController,
    HealthController,
    RuntimeReadinessController,
    GatewayJwtVerifyController,
    BuyerDealAPIController,
    AgentDealAPIController,
  ],
  providers: [
    { provide: RemoteConfigClient, useFactory: sharedConfigClient },
    { provide: APP_FILTER, useClass: AllExceptionsFilter },
    { provide: APP_INTERCEPTOR, useClass: JsonScalarResponseInterceptor },
    { provide: APP_INTERCEPTOR, useClass: MetricsInterceptor },
    OfferService,
    ContractService,
    FunctionsService,
  ],
})
export class AppModule {
}
