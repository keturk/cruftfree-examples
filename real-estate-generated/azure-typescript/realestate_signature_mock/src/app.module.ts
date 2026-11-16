import { Module } from '@nestjs/common';
import { APP_GUARD, APP_FILTER } from '@nestjs/core';
import { SecretsModule } from './realestate_signature_mock/secrets';
import { SettingsModule } from './config/settings';
import { RemoteConfigClient, sharedConfigClient } from './config/remoteConfig';
import { RuntimeReadinessController } from './config/runtime-readiness.controller';
import { MikroOrmModule } from '@mikro-orm/nestjs';
import { VendorEnvelope } from './realestate_signature_mock/entities/signature_db/vendor-envelope.entity';
import { ApiKey } from './realestate_signature_mock/entities/signature_db/api-key.entity';
import { SignatureDbDatabaseModule } from './signature-db/database.module';
import { HealthController } from './observability/health.controller';
import { SignatureAPIController } from './controllers/signature_api.controller';
import { SignatureDeskAPIController } from './controllers/signature_desk_api.controller';
import { _api_key_verifyController } from './controllers/api_key_verify.controller';
import { VendorEnvelopeService } from './services/vendor_envelope.service';
import { ApiKeyService } from './services/api_key.service';
import { APP_INTERCEPTOR } from '@nestjs/core';
import { JsonScalarResponseInterceptor } from './common/json-scalar-response.interceptor';
import { LoggerModule } from './observability/logger.module';
import { TrustedCallerGuard } from './auth/trusted-caller.guard';
import { AllExceptionsFilter } from './errors/all-exceptions-filter';

@Module({
  imports: [
    SettingsModule,
    SecretsModule,
    SignatureDbDatabaseModule,
    MikroOrmModule.forFeature([
      VendorEnvelope,
      ApiKey,
    ]),
    LoggerModule,
  ],
  controllers: [
    HealthController,
    RuntimeReadinessController,
    SignatureAPIController,
    SignatureDeskAPIController,
    _api_key_verifyController,
  ],
  providers: [
    { provide: RemoteConfigClient, useFactory: sharedConfigClient },
    { provide: APP_GUARD, useClass: TrustedCallerGuard },
    { provide: APP_FILTER, useClass: AllExceptionsFilter },
    { provide: APP_INTERCEPTOR, useClass: JsonScalarResponseInterceptor },
    VendorEnvelopeService,
    ApiKeyService,
  ],
})
export class AppModule {
}
