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
import { CardChargeService } from '../services/card_charge.service';
import { ChargeStatus } from '../enums/charge-status.enum';
import { Page } from '../dto/page';
import { PageRequest } from '../dto/page-request.struct';
import { CardCharge } from '../hotel_payment_mock/entities/payment_db/card-charge.entity';
import { projectResponse } from '../support/responseProjection';
import { ApiBearerAuth } from '@nestjs/swagger';

@UseGuards(AuthGuard)
@Controller('api/v1/desk/payment')
export class PaymentDeskAPIController {
  constructor(
    private readonly cardChargeService: CardChargeService,
  ) {}

  @Providers('identity', 'test_auth')
  @PrincipalTypes('human')
  @Roles('operator')
  @ApiBearerAuth()
  @Get('card_charges')
  async listCardCharges(
    @Query('skip', new RejectRepeatedPipe("skip"), new DefaultValuePipe(0), new ParseIntPipe({ exceptionFactory: () => paramFailure("query", "skip", "invalid") }), new IntRangePipe(0, null, "query", "skip")) skip: number,
    @Query('limit', new RejectRepeatedPipe("limit"), new DefaultValuePipe(20), new ParseIntPipe({ exceptionFactory: () => paramFailure("query", "limit", "invalid") }), new IntRangePipe(1, 100, "query", "limit")) limit: number,
    @Query('reference', new RejectRepeatedPipe("reference"), new ValueRulePipe((value: unknown): boolean => (typeof value === 'string') && Array.from(value as string).length <= 80, "query", "reference")) reference: string | null = null,
    @Query('status', new RejectRepeatedPipe("status"), new CoerceStringEnumPipe(ChargeStatus, true, "query", "status")) status: ChargeStatus | null = null,
  ): Promise<Page<CardCharge>> {
    return projectResponse(await (async (): Promise<Page<CardCharge>> => {
      const page = Object.assign(new PageRequest(), { offset: skip, limit: limit });
      return this.cardChargeService.findAll(page, reference, status);
    })(), { kind: 'page', of: { kind: 'entity', entity: 'CardCharge' } });
  }

}
