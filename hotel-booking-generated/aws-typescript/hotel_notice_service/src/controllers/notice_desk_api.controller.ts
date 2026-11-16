import {
  Controller,
  Get,
  Param,
  Query,
  DefaultValuePipe,
  ParseBoolPipe,
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
import { IntRangePipe } from '../pipes/int-range.pipe';
import { ValueRulePipe } from '../pipes/value-rule.pipe';
import { NoticeService } from '../services/notice.service';
import { Page } from '../dto/page';
import { PageRequest } from '../dto/page-request.struct';
import { Notice } from '../hotel_notice_service/entities/notice_db/notice.entity';
import { projectResponse } from '../support/responseProjection';
import { ApiBearerAuth } from '@nestjs/swagger';

@UseGuards(AuthGuard)
@Controller('api/v1/desk/notices')
export class NoticeDeskAPIController {
  constructor(
    private readonly noticeService: NoticeService,
  ) {}

  @Providers('identity')
  @PrincipalTypes('human')
  @Roles('operator')
  @ApiBearerAuth()
  @Get('')
  async listNotices(
    @Query('skip', new RejectRepeatedPipe("skip"), new DefaultValuePipe(0), new ParseIntPipe({ exceptionFactory: () => paramFailure("query", "skip", "invalid") }), new IntRangePipe(0, null, "query", "skip")) skip: number,
    @Query('limit', new RejectRepeatedPipe("limit"), new DefaultValuePipe(20), new ParseIntPipe({ exceptionFactory: () => paramFailure("query", "limit", "invalid") }), new IntRangePipe(1, 100, "query", "limit")) limit: number,
    @Query('recipient', new RejectRepeatedPipe("recipient"), new ValueRulePipe((value: unknown): boolean => (typeof value === 'string') && Array.from(value as string).length <= 200, "query", "recipient")) recipient: string | null = null,
    @Query('delivered', new RejectRepeatedPipe("delivered"), new ParseBoolPipe({ optional: true, exceptionFactory: () => paramFailure("query", "delivered", "invalid") })) delivered: boolean | null = null,
  ): Promise<Page<Notice>> {
    return projectResponse(await (async (): Promise<Page<Notice>> => {
      const page = Object.assign(new PageRequest(), { offset: skip, limit: limit });
      return this.noticeService.findAll(page, recipient, delivered);
    })(), { kind: 'page', of: { kind: 'entity', entity: 'Notice' } });
  }

}
