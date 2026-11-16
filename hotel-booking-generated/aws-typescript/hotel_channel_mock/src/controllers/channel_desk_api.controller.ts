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
import { IntRangePipe } from '../pipes/int-range.pipe';
import { ValueRulePipe } from '../pipes/value-rule.pipe';
import { PublishedNightService } from '../services/published_night.service';
import { Page } from '../dto/page';
import { PageRequest } from '../dto/page-request.struct';
import { PublishedNight } from '../hotel_channel_mock/entities/channel_db/published-night.entity';
import { projectResponse } from '../support/responseProjection';
import { ApiBearerAuth } from '@nestjs/swagger';

@UseGuards(AuthGuard)
@Controller('api/v1/desk/channel')
export class ChannelDeskAPIController {
  constructor(
    private readonly publishedNightService: PublishedNightService,
  ) {}

  @Providers('identity')
  @PrincipalTypes('human')
  @Roles('operator')
  @ApiBearerAuth()
  @Get('published_nights')
  async listPublishedNights(
    @Query('skip', new RejectRepeatedPipe("skip"), new DefaultValuePipe(0), new ParseIntPipe({ exceptionFactory: () => paramFailure("query", "skip", "invalid") }), new IntRangePipe(0, null, "query", "skip")) skip: number,
    @Query('limit', new RejectRepeatedPipe("limit"), new DefaultValuePipe(20), new ParseIntPipe({ exceptionFactory: () => paramFailure("query", "limit", "invalid") }), new IntRangePipe(1, 100, "query", "limit")) limit: number,
    @Query('roomType', new RejectRepeatedPipe("roomType"), new ValueRulePipe((value: unknown): boolean => (typeof value === 'string') && Array.from(value as string).length <= 80, "query", "roomType")) roomType: string | null = null,
    @Query('night', new RejectRepeatedPipe("night")) night: string | null = null,
  ): Promise<Page<PublishedNight>> {
    return projectResponse(await (async (): Promise<Page<PublishedNight>> => {
      const page = Object.assign(new PageRequest(), { offset: skip, limit: limit });
      return this.publishedNightService.findAll(page, roomType, night);
    })(), { kind: 'page', of: { kind: 'entity', entity: 'PublishedNight' } });
  }

}
