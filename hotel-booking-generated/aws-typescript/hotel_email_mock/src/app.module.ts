import { Module } from '@nestjs/common';
import { APP_GUARD, APP_FILTER } from '@nestjs/core';
import { SecretsModule } from './hotel_email_mock/secrets';
import { SettingsModule } from './config/settings';
import { RemoteConfigClient, sharedConfigClient } from './config/remoteConfig';
import { RuntimeReadinessController } from './config/runtime-readiness.controller';
import { MikroOrmModule } from '@mikro-orm/nestjs';
import { Outbound } from './hotel_email_mock/entities/email_db/outbound.entity';
import { ApiKey } from './hotel_email_mock/entities/email_db/api-key.entity';
import { EmailDbDatabaseModule } from './email-db/database.module';
import { MetricsController } from './observability/metrics.controller';
import { HealthController } from './observability/health.controller';
import { EmailAPIController } from './controllers/email_api.controller';
import { EmailDeskAPIController } from './controllers/email_desk_api.controller';
import { _api_key_verifyController } from './controllers/api_key_verify.controller';
import { OutboundService } from './services/outbound.service';
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
    EmailDbDatabaseModule,
    MikroOrmModule.forFeature([
      Outbound,
      ApiKey,
    ]),
    LoggerModule,
  ],
  controllers: [
    MetricsController,
    HealthController,
    RuntimeReadinessController,
    EmailAPIController,
    EmailDeskAPIController,
    _api_key_verifyController,
  ],
  providers: [
    { provide: RemoteConfigClient, useFactory: sharedConfigClient },
    { provide: APP_GUARD, useClass: TrustedCallerGuard },
    { provide: APP_FILTER, useClass: AllExceptionsFilter },
    { provide: APP_INTERCEPTOR, useClass: JsonScalarResponseInterceptor },
    { provide: APP_INTERCEPTOR, useClass: MetricsInterceptor },
    OutboundService,
    ApiKeyService,
  ],
})
export class AppModule {
}
