import { Module } from '@nestjs/common';
import { APP_GUARD, APP_FILTER } from '@nestjs/core';
import { SecretsModule } from './hotel_channel_mock/secrets';
import { SettingsModule } from './config/settings';
import { RemoteConfigClient, sharedConfigClient } from './config/remoteConfig';
import { RuntimeReadinessController } from './config/runtime-readiness.controller';
import { MikroOrmModule } from '@mikro-orm/nestjs';
import { PublishedNight } from './hotel_channel_mock/entities/channel_db/published-night.entity';
import { ApiKey } from './hotel_channel_mock/entities/channel_db/api-key.entity';
import { ChannelDbDatabaseModule } from './channel-db/database.module';
import { MetricsController } from './observability/metrics.controller';
import { HealthController } from './observability/health.controller';
import { ChannelAPIController } from './controllers/channel_api.controller';
import { ChannelDeskAPIController } from './controllers/channel_desk_api.controller';
import { _api_key_verifyController } from './controllers/api_key_verify.controller';
import { PublishedNightService } from './services/published_night.service';
import { ApiKeyService } from './services/api_key.service';
import { APP_INTERCEPTOR } from '@nestjs/core';
import { MetricsInterceptor } from './observability/metrics.interceptor';
import { JsonScalarResponseInterceptor } from './common/json-scalar-response.interceptor';
import { LoggerModule } from './observability/logger.module';
import { TrustedCallerGuard } from './auth/trusted-caller.guard';
import { GatewayJwtVerifyController } from './hotel_channel_mock/gateway-jwt-verify.controller';
import { AllExceptionsFilter } from './errors/all-exceptions-filter';

@Module({
  imports: [
    SettingsModule,
    SecretsModule,
    ChannelDbDatabaseModule,
    MikroOrmModule.forFeature([
      PublishedNight,
      ApiKey,
    ]),
    LoggerModule,
  ],
  controllers: [
    MetricsController,
    HealthController,
    RuntimeReadinessController,
    GatewayJwtVerifyController,
    ChannelAPIController,
    ChannelDeskAPIController,
    _api_key_verifyController,
  ],
  providers: [
    { provide: RemoteConfigClient, useFactory: sharedConfigClient },
    { provide: APP_GUARD, useClass: TrustedCallerGuard },
    { provide: APP_FILTER, useClass: AllExceptionsFilter },
    { provide: APP_INTERCEPTOR, useClass: JsonScalarResponseInterceptor },
    { provide: APP_INTERCEPTOR, useClass: MetricsInterceptor },
    PublishedNightService,
    ApiKeyService,
  ],
})
export class AppModule {
}
