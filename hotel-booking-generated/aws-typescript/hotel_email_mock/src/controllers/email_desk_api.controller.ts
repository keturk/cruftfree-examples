import {
  Controller,
  Get,
  Param,
  Query,
  DefaultValuePipe,
  ParseIntPipe,
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
import { OutboundService } from '../services/outbound.service';
import { DeliveryStatus } from '../enums/delivery-status.enum';
import { Page } from '../dto/page';
import { PageRequest } from '../dto/page-request.struct';
import { Outbound } from '../hotel_email_mock/entities/email_db/outbound.entity';
import { projectResponse } from '../support/responseProjection';
import { ApiBearerAuth } from '@nestjs/swagger';

@UseGuards(AuthGuard)
@Controller('api/v1/desk/email')
export class EmailDeskAPIController {
  constructor(
    private readonly outboundService: OutboundService,
  ) {}

  @Providers('identity')
  @PrincipalTypes('human')
  @Roles('operator')
  @ApiBearerAuth()
  @Get('outbounds')
  async listOutbounds(
    @Query('skip', new RejectRepeatedPipe("skip"), new DefaultValuePipe(0), new ParseIntPipe({ exceptionFactory: () => paramFailure("query", "skip", "invalid") }), new IntRangePipe(0, null, "query", "skip")) skip: number,
    @Query('limit', new RejectRepeatedPipe("limit"), new DefaultValuePipe(20), new ParseIntPipe({ exceptionFactory: () => paramFailure("query", "limit", "invalid") }), new IntRangePipe(1, 100, "query", "limit")) limit: number,
    @Query('recipient', new RejectRepeatedPipe("recipient"), new ValueRulePipe((value: unknown): boolean => (typeof value === 'string') && Array.from(value as string).length <= 200, "query", "recipient")) recipient: string | null = null,
    @Query('subject', new RejectRepeatedPipe("subject"), new ValueRulePipe((value: unknown): boolean => (typeof value === 'string') && Array.from(value as string).length <= 200, "query", "subject")) subject: string | null = null,
    @Query('status', new RejectRepeatedPipe("status"), new CoerceStringEnumPipe(DeliveryStatus, true, "query", "status")) status: DeliveryStatus | null = null,
  ): Promise<Page<Outbound>> {
    return projectResponse(await (async (): Promise<Page<Outbound>> => {
      const page = Object.assign(new PageRequest(), { offset: skip, limit: limit });
      return this.outboundService.findAll(page, recipient, subject, status);
    })(), { kind: 'page', of: { kind: 'entity', entity: 'Outbound' } });
  }

}
