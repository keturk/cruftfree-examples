import { Module } from '@nestjs/common';
import { APP_GUARD, APP_FILTER } from '@nestjs/core';
import { SecretsModule } from './hotel_stay_service/secrets';
import { SettingsModule } from './config/settings';
import { RemoteConfigClient, sharedConfigClient } from './config/remoteConfig';
import { RuntimeReadinessController } from './config/runtime-readiness.controller';
import { MikroOrmModule } from '@mikro-orm/nestjs';
import { RoomType } from './hotel_stay_service/entities/stay_db/room-type.entity';
import { Room } from './hotel_stay_service/entities/stay_db/room.entity';
import { Stay } from './hotel_stay_service/entities/stay_db/stay.entity';
import { StayDbDatabaseModule } from './stay-db/database.module';
import { MetricsController } from './observability/metrics.controller';
import { HealthController } from './observability/health.controller';
import { PubsubHealthService as MqPubsubHealth } from './mq/pubsub.health';
import { StayAPIController } from './controllers/stay_api.controller';
import { DeskAPIController } from './controllers/desk_api.controller';
import { RoomTypeService } from './services/room_type.service';
import { RoomService } from './services/room.service';
import { StayService } from './services/stay.service';
import { APP_INTERCEPTOR } from '@nestjs/core';
import { MetricsInterceptor } from './observability/metrics.interceptor';
import { JsonScalarResponseInterceptor } from './common/json-scalar-response.interceptor';
import { LoggerModule } from './observability/logger.module';
import { TrustedCallerGuard } from './auth/trusted-caller.guard';
import { AllExceptionsFilter } from './errors/all-exceptions-filter';
import { FunctionsService } from './functions';

@Module({
  imports: [
    SettingsModule,
    SecretsModule,
    StayDbDatabaseModule,
    MikroOrmModule.forFeature([
      RoomType,
      Room,
      Stay,
    ]),
    LoggerModule,
  ],
  controllers: [
    MetricsController,
    HealthController,
    RuntimeReadinessController,
    StayAPIController,
    DeskAPIController,
  ],
  providers: [
    { provide: RemoteConfigClient, useFactory: sharedConfigClient },
    { provide: APP_GUARD, useClass: TrustedCallerGuard },
    { provide: APP_FILTER, useClass: AllExceptionsFilter },
    { provide: APP_INTERCEPTOR, useClass: JsonScalarResponseInterceptor },
    { provide: APP_INTERCEPTOR, useClass: MetricsInterceptor },
    MqPubsubHealth,
    RoomTypeService,
    RoomService,
    StayService,
    FunctionsService,
  ],
})
export class AppModule {
}
