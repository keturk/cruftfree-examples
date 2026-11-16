import { Module } from '@nestjs/common';
import { APP_GUARD, APP_FILTER } from '@nestjs/core';
import { SecretsModule } from './hotel_notice_service/secrets';
import { SettingsModule } from './config/settings';
import { RemoteConfigClient, sharedConfigClient } from './config/remoteConfig';
import { RuntimeReadinessController } from './config/runtime-readiness.controller';
import { MikroOrmModule } from '@mikro-orm/nestjs';
import { Notice } from './hotel_notice_service/entities/notice_db/notice.entity';
import { NoticeDbDatabaseModule } from './notice-db/database.module';
import { CqrsModule } from '@nestjs/cqrs';
import { MetricsController } from './observability/metrics.controller';
import { HealthController } from './observability/health.controller';
import { NoticeDeskAPIController } from './controllers/notice_desk_api.controller';
import { NoticeService } from './services/notice.service';
import { APP_INTERCEPTOR } from '@nestjs/core';
import { MetricsInterceptor } from './observability/metrics.interceptor';
import { JsonScalarResponseInterceptor } from './common/json-scalar-response.interceptor';
import { LoggerModule } from './observability/logger.module';
import { TrustedCallerGuard } from './auth/trusted-caller.guard';
import { HttpClientsModule } from './http-clients.module';
import { AllExceptionsFilter } from './errors/all-exceptions-filter';
import { FunctionsService } from './functions';

@Module({
  imports: [
    SettingsModule,
    SecretsModule,
    NoticeDbDatabaseModule,
    MikroOrmModule.forFeature([
      Notice,
    ]),
    CqrsModule.forRoot(),
    LoggerModule,
    HttpClientsModule,
  ],
  controllers: [
    MetricsController,
    HealthController,
    RuntimeReadinessController,
    NoticeDeskAPIController,
  ],
  providers: [
    { provide: RemoteConfigClient, useFactory: sharedConfigClient },
    { provide: APP_GUARD, useClass: TrustedCallerGuard },
    { provide: APP_FILTER, useClass: AllExceptionsFilter },
    { provide: APP_INTERCEPTOR, useClass: JsonScalarResponseInterceptor },
    { provide: APP_INTERCEPTOR, useClass: MetricsInterceptor },
    NoticeService,
    FunctionsService,
  ],
})
export class AppModule {
}
