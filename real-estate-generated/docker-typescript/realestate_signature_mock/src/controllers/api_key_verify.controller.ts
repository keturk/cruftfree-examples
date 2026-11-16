import {
  Controller,
  Post,
  Param,
  HttpCode,
  HttpStatus,
  UseGuards,
} from '@nestjs/common';
import { AuthGuard } from '../auth/auth.guard';
import { PrincipalTypes } from '../auth/optional-auth.decorator';
import { Providers } from '../auth/providers.decorator';
import { RequestBody, paramFailure } from '../common/request-validation';
import { ApiKeyVerifyRequest } from '../dto/api-key-verify-request.struct';
import { ApiKeyVerifyResponse } from '../auth/api-key-verify';
import { answerApiKeyVerifyRequest } from '../auth/api-key-verify';
import { ApiExtraModels, ApiExcludeEndpoint, ApiBearerAuth } from '@nestjs/swagger';

@ApiExtraModels(ApiKeyVerifyRequest)
@UseGuards(AuthGuard)
@Controller('internal/identity/api-keys')
export class _api_key_verifyController {
  constructor(
  ) {}

  @Providers('machine', 'test_auth')
  @PrincipalTypes('machine')
  @ApiExcludeEndpoint()
  @ApiBearerAuth()
  @Post('signatureKeys/verify')
  @HttpCode(HttpStatus.CREATED)
  async postSignatureKeysVerify(
    @RequestBody("object") body: ApiKeyVerifyRequest,
  ): Promise<ApiKeyVerifyResponse> {
    return answerApiKeyVerifyRequest("signatureKeys", body.keyHash);
  }

}
