import {
  Controller,
  Get,
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
import { InjectRepository } from '@mikro-orm/nestjs';
import { EntityRepository } from '@mikro-orm/core';
import { Envelope } from '../dto/envelope.struct';
import { SendEnvelopeRequest } from '../dto/send-envelope-request.struct';
import { VendorEnvelope } from '../realestate_signature_mock/entities/signature_db/vendor-envelope.entity';
import { NoSuchEnvelopeError } from '../errors/domain-errors';
import { SqlEntityManager } from '@mikro-orm/postgresql';
import { answerOf } from '../functions';
import { randomInt } from 'crypto';
import { ApiExtraModels, ApiResponse, ApiSecurity } from '@nestjs/swagger';

@ApiExtraModels(Envelope, SendEnvelopeRequest)
@UseGuards(AuthGuard)
@Controller('v1')
export class SignatureAPIController {
  constructor(
    @InjectRepository(VendorEnvelope) private readonly vendorEnvelopeRepository: EntityRepository<VendorEnvelope>,
  ) {}

  @Providers('signatureKeys', 'test_auth')
  @PrincipalTypes('human')
  @ApiSecurity("signatureKeys")
  @Post('envelopes')
  @HttpCode(HttpStatus.CREATED)
  @ApiResponse({ status: 201, type: Envelope })
  async postEnvelopes(
    @RequestBody("object") body: SendEnvelopeRequest,
  ): Promise<Envelope> {
    const existing: VendorEnvelope | null = (await (this.vendorEnvelopeRepository.getEntityManager() as SqlEntityManager).createQueryBuilder(VendorEnvelope, 'e_vendor_envelope').select('*').where('e_vendor_envelope.idempotency_key = ?', [body.idempotencyKey]).limit(1).getResultList())[0] ?? null;
    if ((existing != null)) {
      return await answerOf(existing);
    }
    return await answerOf(this.vendorEnvelopeRepository.create({ envelopeId: `env_${Array.from({ length: 24 }, () => '0123456789abcdef'.charAt(randomInt('0123456789abcdef'.length))).join('')}`, idempotencyKey: body.idempotencyKey, signerName: body.signerName, signerEmail: body.signerEmail, documentTitle: body.documentTitle, documentBody: body.documentBody } as never));
  }

  @Providers('signatureKeys', 'test_auth')
  @PrincipalTypes('human')
  @ApiSecurity("signatureKeys")
  @Get('envelopes/:id')
  @ApiResponse({ status: 200, type: Envelope })
  async getEnvelopesById(
    @Param('id') id: string,
  ): Promise<Envelope> {
    const envelope: VendorEnvelope | null = (await (this.vendorEnvelopeRepository.getEntityManager() as SqlEntityManager).createQueryBuilder(VendorEnvelope, 'e_vendor_envelope').select('*').where('e_vendor_envelope.envelope_id = ?', [id]).limit(1).getResultList())[0] ?? null;
    if ((envelope == null)) {
      throw new NoSuchEnvelopeError({});
    }
    return await answerOf(envelope);
  }

}
