import {
  Controller,
  Get,
  Post,
  Param,
  ParseUUIDPipe,
  Req,
  HttpCode,
  HttpStatus,
  UseGuards,
} from '@nestjs/common';
import type { Request } from 'express';
import { AuthGuard } from '../auth/auth.guard';
import { PrincipalTypes } from '../auth/optional-auth.decorator';
import { Providers } from '../auth/providers.decorator';
import { RequestBody, paramFailure } from '../common/request-validation';
import { InjectRepository } from '@mikro-orm/nestjs';
import { EntityRepository } from '@mikro-orm/core';
import { ViewingService } from '../services/viewing.service';
import { ListingStatus } from '../enums/listing-status.enum';
import { RequestViewing } from '../dto/request-viewing.struct';
import { ViewingStatus } from '../enums/viewing-status.enum';
import { Viewing } from '../realestate_viewing_service/entities/viewing_db/viewing.entity';
import { InThePastError } from '../errors/domain-errors';
import { NotOpenForViewingsError } from '../errors/domain-errors';
import { NotYourViewingError } from '../errors/domain-errors';
import { ListingServiceListingFactsResponse } from '../clients/realestate-listing-service-responses';
import { SqlEntityManager } from '@mikro-orm/postgresql';
import { UnauthorizedException } from '@nestjs/common';
import { VIEWING_MINUTES } from '../constants';
import { addMinutes } from 'date-fns';
import { projectResponse } from '../support/responseProjection';
import { realestateListingServiceClient } from '../clients/realestate-listing-service-client.service';
import { ApiExtraModels, ApiBearerAuth } from '@nestjs/swagger';

@ApiExtraModels(RequestViewing)
@UseGuards(AuthGuard)
@Controller('api/v1/viewings')
export class BuyerViewingAPIController {
  constructor(
    private readonly viewingService: ViewingService,
    @InjectRepository(Viewing) private readonly viewingRepository: EntityRepository<Viewing>,
  ) {}

  @Providers('identity')
  @PrincipalTypes('human')
  @ApiBearerAuth()
  @Get('mine')
  async getMine(
    @Req() req: Request,
  ): Promise<Viewing[]> {
    return projectResponse(await (async (): Promise<Viewing[]> => {
      return await (this.viewingRepository.getEntityManager() as SqlEntityManager).createQueryBuilder(Viewing, 'e_viewing').select('*').where('e_viewing.buyer_email = ?', [((req.user ?? (() => { throw new UnauthorizedException({ type: 'about:blank', title: 'Unauthorized', status: 401 }); })()).identity.email as string)]).orderBy({ 'e_viewing.starts_at': 'DESC' }).limit(50).getResultList();
    })(), { kind: 'list', of: { kind: 'entity', entity: 'Viewing' } });
  }

  @Providers('identity')
  @PrincipalTypes('human')
  @ApiBearerAuth()
  @Post('request')
  @HttpCode(HttpStatus.CREATED)
  async postRequest(
    @RequestBody("object") body: RequestViewing,
    @Req() req: Request,
  ): Promise<Viewing> {
    return projectResponse(await (async (): Promise<Viewing> => {
      const listing: ListingServiceListingFactsResponse = (await realestateListingServiceClient().get(`/internal/listings/facts/${body.listingId}`, {}, false)).data;
      if ((listing['status'] !== ListingStatus.Active)) {
        throw new NotOpenForViewingsError({});
      }
      if ((body.startsAt < new Date())) {
        throw new InThePastError({});
      }
      const entity = this.viewingRepository.create({ listingId: body.listingId, listingTitle: listing['title'], startsAt: body.startsAt, endsAt: addMinutes(body.startsAt, VIEWING_MINUTES), note: body.note, buyerName: String(((((req.user ?? (() => { throw new UnauthorizedException({ type: 'about:blank', title: 'Unauthorized', status: 401 }); })()).identity.fullName ?? null) as string | null) ?? ((req.user ?? (() => { throw new UnauthorizedException({ type: 'about:blank', title: 'Unauthorized', status: 401 }); })()).identity.email as string))), buyerEmail: ((req.user ?? (() => { throw new UnauthorizedException({ type: 'about:blank', title: 'Unauthorized', status: 401 }); })()).identity.email as string), agentName: listing['agentName'], agentEmail: listing['agentEmail'] } as never);
      await this.viewingRepository.getEntityManager().persistAndFlush(entity);
      return entity
    })(), { kind: 'entity', entity: 'Viewing' });
  }

  @Providers('identity')
  @PrincipalTypes('human')
  @ApiBearerAuth()
  @Post('cancel/:id')
  @HttpCode(HttpStatus.CREATED)
  async postCancelById(
    @Param('id', new ParseUUIDPipe({ exceptionFactory: () => paramFailure("path", "id", "invalid") })) id: string,
    @Req() req: Request,
  ): Promise<Viewing> {
    return projectResponse(await (async (): Promise<Viewing> => {
      const viewing: Viewing | null = (await (this.viewingRepository.getEntityManager() as SqlEntityManager).createQueryBuilder(Viewing, 'e_viewing').select('*').where('e_viewing.id = ?', [id]).andWhere('e_viewing.buyer_email = ?', [((req.user ?? (() => { throw new UnauthorizedException({ type: 'about:blank', title: 'Unauthorized', status: 401 }); })()).identity.email as string)]).limit(1).getResultList())[0] ?? null;
      if ((viewing == null)) {
        throw new NotYourViewingError({});
      }
      viewing.status = ViewingStatus.Cancelled;
      await this.viewingRepository.getEntityManager().persistAndFlush(viewing);
      return viewing;
    })(), { kind: 'entity', entity: 'Viewing' });
  }

}
