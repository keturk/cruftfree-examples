import { Module } from '@nestjs/common';
import { APP_GUARD, APP_FILTER } from '@nestjs/core';
import { SecretsModule } from './realestate_mortgage_mock/secrets';
import { SettingsModule } from './config/settings';
import { RemoteConfigClient, sharedConfigClient } from './config/remoteConfig';
import { RuntimeReadinessController } from './config/runtime-readiness.controller';
import { MikroOrmModule } from '@mikro-orm/nestjs';
import { LenderAnswer } from './realestate_mortgage_mock/entities/mortgage_db/lender-answer.entity';
import { ApiKey } from './realestate_mortgage_mock/entities/mortgage_db/api-key.entity';
import { MortgageDbDatabaseModule } from './mortgage-db/database.module';
import { MetricsController } from './observability/metrics.controller';
import { HealthController } from './observability/health.controller';
import { MortgageAPIController } from './controllers/mortgage_api.controller';
import { MortgageDeskAPIController } from './controllers/mortgage_desk_api.controller';
import { _api_key_verifyController } from './controllers/api_key_verify.controller';
import { LenderAnswerService } from './services/lender_answer.service';
import { ApiKeyService } from './services/api_key.service';
import { APP_INTERCEPTOR } from '@nestjs/core';
import { MetricsInterceptor } from './observability/metrics.interceptor';
import { JsonScalarResponseInterceptor } from './common/json-scalar-response.interceptor';
import { LoggerModule } from './observability/logger.module';
import { getThrottlerModule } from './realestate_mortgage_mock/gateway-throttler.config';
import { AllExceptionsFilter } from './errors/all-exceptions-filter';

@Module({
  imports: [
    SettingsModule,
    SecretsModule,
    MortgageDbDatabaseModule,
    MikroOrmModule.forFeature([
      LenderAnswer,
      ApiKey,
    ]),
    getThrottlerModule(),
    LoggerModule,
  ],
  controllers: [
    MetricsController,
    HealthController,
    RuntimeReadinessController,
    MortgageAPIController,
    MortgageDeskAPIController,
    _api_key_verifyController,
  ],
  providers: [
    { provide: RemoteConfigClient, useFactory: sharedConfigClient },
    { provide: APP_FILTER, useClass: AllExceptionsFilter },
    { provide: APP_INTERCEPTOR, useClass: JsonScalarResponseInterceptor },
    { provide: APP_INTERCEPTOR, useClass: MetricsInterceptor },
    LenderAnswerService,
    ApiKeyService,
  ],
})
export class AppModule {
}
