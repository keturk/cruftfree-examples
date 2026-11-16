import {
  Controller,
  Get,
  Post,
  Param,
  Query,
  DefaultValuePipe,
  ParseIntPipe,
  ParseUUIDPipe,
  HttpCode,
  HttpStatus,
  UseGuards,
} from '@nestjs/common';
import { AuthGuard } from '../auth/auth.guard';
import { PrincipalTypes } from '../auth/optional-auth.decorator';
import { Roles } from '../auth/roles.decorator';
import { Providers } from '../auth/providers.decorator';
import { RejectRepeatedPipe, paramFailure } from '../common/request-validation';
import { CoerceStringEnumPipe } from '../pipes/string-enum-query.pipe';
import { IntRangePipe } from '../pipes/int-range.pipe';
import { ValueRulePipe } from '../pipes/value-rule.pipe';
import { InjectRepository } from '@mikro-orm/nestjs';
import { EntityRepository } from '@mikro-orm/core';
import { VendorEnvelopeService } from '../services/vendor_envelope.service';
import { EnvelopeStatus } from '../enums/envelope-status.enum';
import { Page } from '../dto/page';
import { PageRequest } from '../dto/page-request.struct';
import { VendorEnvelope } from '../realestate_signature_mock/entities/signature_db/vendor-envelope.entity';
import { NotFoundException } from '@nestjs/common';
import { projectResponse } from '../support/responseProjection';
import { ApiBearerAuth } from '@nestjs/swagger';

@UseGuards(AuthGuard)
@Controller('api/v1/desk/signature')
export class SignatureDeskAPIController {
  constructor(
    private readonly vendorEnvelopeService: VendorEnvelopeService,
    @InjectRepository(VendorEnvelope) private readonly vendorEnvelopeRepository: EntityRepository<VendorEnvelope>,
  ) {}

  @Providers('identity')
  @PrincipalTypes('human')
  @Roles('operator')
  @ApiBearerAuth()
  @Get('vendor_envelopes')
  async listVendorEnvelopes(
    @Query('skip', new RejectRepeatedPipe("skip"), new DefaultValuePipe(0), new ParseIntPipe({ exceptionFactory: () => paramFailure("query", "skip", "invalid") }), new IntRangePipe(0, null, "query", "skip")) skip: number,
    @Query('limit', new RejectRepeatedPipe("limit"), new DefaultValuePipe(20), new ParseIntPipe({ exceptionFactory: () => paramFailure("query", "limit", "invalid") }), new IntRangePipe(1, 100, "query", "limit")) limit: number,
    @Query('signerName', new RejectRepeatedPipe("signerName"), new ValueRulePipe((value: unknown): boolean => (typeof value === 'string') && Array.from(value as string).length <= 200, "query", "signerName")) signerName: string | null = null,
    @Query('documentTitle', new RejectRepeatedPipe("documentTitle"), new ValueRulePipe((value: unknown): boolean => (typeof value === 'string') && Array.from(value as string).length <= 200, "query", "documentTitle")) documentTitle: string | null = null,
    @Query('status', new RejectRepeatedPipe("status"), new CoerceStringEnumPipe(EnvelopeStatus, true, "query", "status")) status: EnvelopeStatus | null = null,
  ): Promise<Page<VendorEnvelope>> {
    return projectResponse(await (async (): Promise<Page<VendorEnvelope>> => {
      const page = Object.assign(new PageRequest(), { offset: skip, limit: limit });
      return this.vendorEnvelopeService.findAll(page, signerName, documentTitle, status);
    })(), { kind: 'page', of: { kind: 'entity', entity: 'VendorEnvelope' } });
  }

  @Providers('identity')
  @PrincipalTypes('human')
  @Roles('operator')
  @ApiBearerAuth()
  @Post('decline/:id')
  @HttpCode(HttpStatus.CREATED)
  async postDeclineById(
    @Param('id', new ParseUUIDPipe({ exceptionFactory: () => paramFailure("path", "id", "invalid") })) id: string,
  ): Promise<VendorEnvelope> {
    return projectResponse(await (async (): Promise<VendorEnvelope> => {
      const envelope = await this.vendorEnvelopeRepository.findOne({ id: id });
      if (!envelope) {
        throw new NotFoundException("Not found");
      }
      envelope.status = EnvelopeStatus.Declined;
      envelope.settledAt = new Date();
      await this.vendorEnvelopeRepository.getEntityManager().persistAndFlush(envelope);
      return envelope;
    })(), { kind: 'entity', entity: 'VendorEnvelope' });
  }

  @Providers('identity')
  @PrincipalTypes('human')
  @Roles('operator')
  @ApiBearerAuth()
  @Post('sign/:id')
  @HttpCode(HttpStatus.CREATED)
  async postSignById(
    @Param('id', new ParseUUIDPipe({ exceptionFactory: () => paramFailure("path", "id", "invalid") })) id: string,
  ): Promise<VendorEnvelope> {
    return projectResponse(await (async (): Promise<VendorEnvelope> => {
      const envelope = await this.vendorEnvelopeRepository.findOne({ id: id });
      if (!envelope) {
        throw new NotFoundException("Not found");
      }
      envelope.status = EnvelopeStatus.Signed;
      envelope.settledAt = new Date();
      await this.vendorEnvelopeRepository.getEntityManager().persistAndFlush(envelope);
      return envelope;
    })(), { kind: 'entity', entity: 'VendorEnvelope' });
  }

}
