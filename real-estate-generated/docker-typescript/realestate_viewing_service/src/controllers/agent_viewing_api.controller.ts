import {
  Controller,
  Get,
  Post,
  Param,
  Query,
  DefaultValuePipe,
  ParseIntPipe,
  ParseUUIDPipe,
  Req,
  HttpCode,
  HttpStatus,
  UseGuards,
} from '@nestjs/common';
import type { Request } from 'express';
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
import { FunctionsService } from '../functions';
import { ViewingService } from '../services/viewing.service';
import { Page } from '../dto/page';
import { PageRequest } from '../dto/page-request.struct';
import { ViewingStatus } from '../enums/viewing-status.enum';
import { ViewingSummary } from '../dto/viewing-summary.struct';
import { Viewing } from '../realestate_viewing_service/entities/viewing_db/viewing.entity';
import { AgentBusyError } from '../errors/domain-errors';
import { WrongStepError } from '../errors/domain-errors';
import { SqlEntityManager } from '@mikro-orm/postgresql';
import { UnauthorizedException } from '@nestjs/common';
import { VIEWING_MINUTES } from '../constants';
import { addDays } from 'date-fns';
import { addMinutes } from 'date-fns';
import { format } from 'date-fns';
import { projectResponse } from '../support/responseProjection';
import { sendMail } from '../functions';
import { ApiExtraModels, ApiResponse, ApiBearerAuth } from '@nestjs/swagger';

@ApiExtraModels(ViewingSummary)
@UseGuards(AuthGuard)
@Controller('api/v1/agent/viewings')
export class AgentViewingAPIController {
  constructor(
    private readonly functionsService: FunctionsService,
    private readonly viewingService: ViewingService,
    @InjectRepository(Viewing) private readonly viewingRepository: EntityRepository<Viewing>,
  ) {}

  @Providers('identity', 'test_auth')
  @PrincipalTypes('human')
  @Roles('agent')
  @ApiBearerAuth()
  @Get('calendar')
  async getCalendar(
    @Req() req: Request,
  ): Promise<Viewing[]> {
    return projectResponse(await (async (): Promise<Viewing[]> => {
      return await (this.viewingRepository.getEntityManager() as SqlEntityManager).createQueryBuilder(Viewing, 'e_viewing').select('*').where('e_viewing.agent_email = ?', [((req.user ?? (() => { throw new UnauthorizedException({ type: 'about:blank', title: 'Unauthorized', status: 401 }); })()).identity.email as string)]).andWhere({ status: ViewingStatus.Confirmed }).orderBy({ 'e_viewing.starts_at': 'ASC' }).limit(200).getResultList();
    })(), { kind: 'list', of: { kind: 'entity', entity: 'Viewing' } });
  }

  @Providers('identity', 'test_auth')
  @PrincipalTypes('human')
  @Roles('agent')
  @ApiBearerAuth()
  @Get('summary')
  @ApiResponse({ status: 200, type: ViewingSummary })
  async getSummary(
    @Req() req: Request,
  ): Promise<ViewingSummary> {
    const me: string = String(((req.user ?? (() => { throw new UnauthorizedException({ type: 'about:blank', title: 'Unauthorized', status: 401 }); })()).identity.email as string));
    const days: number[] = [0, 1, 2, 3, 4, 5, 6];
    return Object.assign(new ViewingSummary(), { waitingForYou: await (this.viewingRepository.getEntityManager() as SqlEntityManager).createQueryBuilder(Viewing, 'e_viewing').select('*').where('e_viewing.agent_email = ?', [me]).andWhere({ status: ViewingStatus.Requested }).getCount(), nextSevenDays: await (this.viewingRepository.getEntityManager() as SqlEntityManager).createQueryBuilder(Viewing, 'e_viewing').select('*').where('e_viewing.agent_email = ?', [me]).andWhere({ status: ViewingStatus.Confirmed }).andWhere('e_viewing.starts_at >= ?', [new Date()]).andWhere('e_viewing.starts_at < ?', [addDays(new Date(), 7)]).getCount(), ahead: await Promise.all(days.map(async (d) => await this.functionsService.dayLoad(me, d))) });
  }

  @Providers('identity', 'test_auth')
  @PrincipalTypes('human')
  @Roles('agent')
  @ApiBearerAuth()
  @Get('')
  async listViewings(
    @Query('skip', new RejectRepeatedPipe("skip"), new DefaultValuePipe(0), new ParseIntPipe({ exceptionFactory: () => paramFailure("query", "skip", "invalid") }), new IntRangePipe(0, null, "query", "skip")) skip: number,
    @Query('limit', new RejectRepeatedPipe("limit"), new DefaultValuePipe(20), new ParseIntPipe({ exceptionFactory: () => paramFailure("query", "limit", "invalid") }), new IntRangePipe(1, 100, "query", "limit")) limit: number,
    @Query('listingTitle', new RejectRepeatedPipe("listingTitle"), new ValueRulePipe((value: unknown): boolean => (typeof value === 'string') && Array.from(value as string).length <= 200, "query", "listingTitle")) listingTitle: string | null = null,
    @Query('buyerName', new RejectRepeatedPipe("buyerName"), new ValueRulePipe((value: unknown): boolean => (typeof value === 'string') && Array.from(value as string).length <= 200, "query", "buyerName")) buyerName: string | null = null,
    @Query('status', new RejectRepeatedPipe("status"), new CoerceStringEnumPipe(ViewingStatus, true, "query", "status")) status: ViewingStatus | null = null,
    @Query('agentName', new RejectRepeatedPipe("agentName"), new ValueRulePipe((value: unknown): boolean => (typeof value === 'string') && Array.from(value as string).length <= 200, "query", "agentName")) agentName: string | null = null,
  ): Promise<Page<Viewing>> {
    return projectResponse(await (async (): Promise<Page<Viewing>> => {
      const page = Object.assign(new PageRequest(), { offset: skip, limit: limit });
      return this.viewingService.findAll(page, listingTitle, buyerName, status, agentName);
    })(), { kind: 'page', of: { kind: 'entity', entity: 'Viewing' } });
  }

  @Providers('identity', 'test_auth')
  @PrincipalTypes('human')
  @Roles('agent')
  @ApiBearerAuth()
  @Post('completed/:id')
  @HttpCode(HttpStatus.CREATED)
  async postCompletedById(
    @Param('id', new ParseUUIDPipe({ exceptionFactory: () => paramFailure("path", "id", "invalid") })) id: string,
  ): Promise<Viewing> {
    return projectResponse(await (async (): Promise<Viewing> => {
      const viewing: Viewing = await this.functionsService.ownAsAgent(id);
      if ((viewing.status !== ViewingStatus.Confirmed)) {
        throw new WrongStepError({});
      }
      viewing.status = ViewingStatus.Completed;
      await this.viewingRepository.getEntityManager().persistAndFlush(viewing);
      return viewing;
    })(), { kind: 'entity', entity: 'Viewing' });
  }

  @Providers('identity', 'test_auth')
  @PrincipalTypes('human')
  @Roles('agent')
  @ApiBearerAuth()
  @Post('confirm/:id')
  @HttpCode(HttpStatus.CREATED)
  async postConfirmById(
    @Param('id', new ParseUUIDPipe({ exceptionFactory: () => paramFailure("path", "id", "invalid") })) id: string,
  ): Promise<Viewing> {
    return projectResponse(await (async (): Promise<Viewing> => {
      const viewing: Viewing = await this.functionsService.ownAsAgent(id);
      if ((viewing.status !== ViewingStatus.Requested)) {
        throw new WrongStepError({});
      }
      const clashes: number = await (this.viewingRepository.getEntityManager() as SqlEntityManager).createQueryBuilder(Viewing, 'e_viewing').select('*').where('e_viewing.agent_email = ?', [viewing.agentEmail]).andWhere({ status: ViewingStatus.Confirmed }).andWhere('e_viewing.starts_at >= ?', [addMinutes(viewing.startsAt, ((-VIEWING_MINUTES) + 1))]).andWhere('e_viewing.starts_at < ?', [viewing.endsAt]).getCount();
      if ((clashes > 0)) {
        throw new AgentBusyError({});
      }
      viewing.status = ViewingStatus.Confirmed;
      await this.viewingRepository.getEntityManager().persistAndFlush(viewing);
      await sendMail(String(viewing.buyerEmail), `Your viewing of ${viewing.listingTitle}`, `${viewing.agentName} will meet you on ${format(viewing.startsAt, 'MMM dd')} at ${format(viewing.startsAt, 'HH:mm')}.`, `confirmed-${viewing.id}`);
      return viewing;
    })(), { kind: 'entity', entity: 'Viewing' });
  }

  @Providers('identity', 'test_auth')
  @PrincipalTypes('human')
  @Roles('agent')
  @ApiBearerAuth()
  @Post('no-show/:id')
  @HttpCode(HttpStatus.CREATED)
  async postNoShowById(
    @Param('id', new ParseUUIDPipe({ exceptionFactory: () => paramFailure("path", "id", "invalid") })) id: string,
  ): Promise<Viewing> {
    return projectResponse(await (async (): Promise<Viewing> => {
      const viewing: Viewing = await this.functionsService.ownAsAgent(id);
      if ((viewing.status !== ViewingStatus.Confirmed)) {
        throw new WrongStepError({});
      }
      viewing.status = ViewingStatus.NoShow;
      await this.viewingRepository.getEntityManager().persistAndFlush(viewing);
      return viewing;
    })(), { kind: 'entity', entity: 'Viewing' });
  }

}
