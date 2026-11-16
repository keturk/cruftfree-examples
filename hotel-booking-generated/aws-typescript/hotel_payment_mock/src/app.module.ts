import { Module } from '@nestjs/common';
import { APP_GUARD, APP_FILTER } from '@nestjs/core';
import { SecretsModule } from './hotel_payment_mock/secrets';
import { SettingsModule } from './config/settings';
import { RemoteConfigClient, sharedConfigClient } from './config/remoteConfig';
import { RuntimeReadinessController } from './config/runtime-readiness.controller';
import { MikroOrmModule } from '@mikro-orm/nestjs';
import { CardCharge } from './hotel_payment_mock/entities/payment_db/card-charge.entity';
import { ApiKey } from './hotel_payment_mock/entities/payment_db/api-key.entity';
import { PaymentDbDatabaseModule } from './payment-db/database.module';
import { MetricsController } from './observability/metrics.controller';
import { HealthController } from './observability/health.controller';
import { PaymentAPIController } from './controllers/payment_api.controller';
import { PaymentDeskAPIController } from './controllers/payment_desk_api.controller';
import { _api_key_verifyController } from './controllers/api_key_verify.controller';
import { CardChargeService } from './services/card_charge.service';
import { ApiKeyService } from './services/api_key.service';
import { APP_INTERCEPTOR } from '@nestjs/core';
import { MetricsInterceptor } from './observability/metrics.interceptor';
import { JsonScalarResponseInterceptor } from './common/json-scalar-response.interceptor';
import { LoggerModule } from './observability/logger.module';
import { TrustedCallerGuard } from './auth/trusted-caller.guard';
import { AllExceptionsFilter } from './errors/all-exceptions-filter';

@Module({
  imports: [
    SettingsModule,
    SecretsModule,
    PaymentDbDatabaseModule,
    MikroOrmModule.forFeature([
      CardCharge,
      ApiKey,
    ]),
    LoggerModule,
  ],
  controllers: [
    MetricsController,
    HealthController,
    RuntimeReadinessController,
    PaymentAPIController,
    PaymentDeskAPIController,
    _api_key_verifyController,
  ],
  providers: [
    { provide: RemoteConfigClient, useFactory: sharedConfigClient },
    { provide: APP_GUARD, useClass: TrustedCallerGuard },
    { provide: APP_FILTER, useClass: AllExceptionsFilter },
    { provide: APP_INTERCEPTOR, useClass: JsonScalarResponseInterceptor },
    { provide: APP_INTERCEPTOR, useClass: MetricsInterceptor },
    CardChargeService,
    ApiKeyService,
  ],
})
export class AppModule {
}
