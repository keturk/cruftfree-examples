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
import { LenderAnswerService } from '../services/lender_answer.service';
import { Page } from '../dto/page';
import { PageRequest } from '../dto/page-request.struct';
import { PreapprovalDecision } from '../enums/preapproval-decision.enum';
import { LenderAnswer } from '../realestate_mortgage_mock/entities/mortgage_db/lender-answer.entity';
import { projectResponse } from '../support/responseProjection';
import { ApiBearerAuth } from '@nestjs/swagger';

@UseGuards(AuthGuard)
@Controller('api/v1/desk/mortgage')
export class MortgageDeskAPIController {
  constructor(
    private readonly lenderAnswerService: LenderAnswerService,
  ) {}

  @Providers('identity', 'test_auth')
  @PrincipalTypes('human')
  @Roles('operator')
  @ApiBearerAuth()
  @Get('lender_answers')
  async listLenderAnswers(
    @Query('skip', new RejectRepeatedPipe("skip"), new DefaultValuePipe(0), new ParseIntPipe({ exceptionFactory: () => paramFailure("query", "skip", "invalid") }), new IntRangePipe(0, null, "query", "skip")) skip: number,
    @Query('limit', new RejectRepeatedPipe("limit"), new DefaultValuePipe(20), new ParseIntPipe({ exceptionFactory: () => paramFailure("query", "limit", "invalid") }), new IntRangePipe(1, 100, "query", "limit")) limit: number,
    @Query('applicantName', new RejectRepeatedPipe("applicantName"), new ValueRulePipe((value: unknown): boolean => (typeof value === 'string') && Array.from(value as string).length <= 200, "query", "applicantName")) applicantName: string | null = null,
    @Query('decision', new RejectRepeatedPipe("decision"), new CoerceStringEnumPipe(PreapprovalDecision, true, "query", "decision")) decision: PreapprovalDecision | null = null,
  ): Promise<Page<LenderAnswer>> {
    return projectResponse(await (async (): Promise<Page<LenderAnswer>> => {
      const page = Object.assign(new PageRequest(), { offset: skip, limit: limit });
      return this.lenderAnswerService.findAll(page, applicantName, decision);
    })(), { kind: 'page', of: { kind: 'entity', entity: 'LenderAnswer' } });
  }

}
