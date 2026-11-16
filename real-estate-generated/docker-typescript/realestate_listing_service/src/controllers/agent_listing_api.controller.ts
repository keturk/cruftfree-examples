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
import { RequestBody, RejectRepeatedPipe, paramFailure } from '../common/request-validation';
import { CoerceStringEnumPipe } from '../pipes/string-enum-query.pipe';
import { IntRangePipe } from '../pipes/int-range.pipe';
import { ValueRulePipe } from '../pipes/value-rule.pipe';
import { InjectRepository } from '@mikro-orm/nestjs';
import { EntityRepository } from '@mikro-orm/core';
import { FunctionsService } from '../functions';
import { ListingService } from '../services/listing.service';
import { NeighbourhoodService } from '../services/neighbourhood.service';
import { AgentSummary } from '../dto/agent-summary.struct';
import { ListingPage } from '../dto/listing-page.struct';
import { ListingStatus } from '../enums/listing-status.enum';
import { NewListing } from '../dto/new-listing.struct';
import { NewPrice } from '../dto/new-price.struct';
import { Page } from '../dto/page';
import { PageRequest } from '../dto/page-request.struct';
import { PropertyKind } from '../enums/property-kind.enum';
import { Listing } from '../realestate_listing_service/entities/listing_db/listing.entity';
import { Neighbourhood } from '../realestate_listing_service/entities/listing_db/neighbourhood.entity';
import { PriceChange } from '../realestate_listing_service/entities/listing_db/price-change.entity';
import { NotFoundException } from '@nestjs/common';
import { UnauthorizedException } from '@nestjs/common';
import { SamePriceError } from '../errors/domain-errors';
import { WrongStepError } from '../errors/domain-errors';
import { SqlEntityManager } from '@mikro-orm/postgresql';
import { _decimalEquals } from '../realestate_listing_service/_decimalHelpers';
import { getProducer as getMqProducer } from '../mq/producer';
import { projectResponse } from '../support/responseProjection';
import { ApiExtraModels, ApiResponse, ApiBearerAuth } from '@nestjs/swagger';

@ApiExtraModels(AgentSummary, ListingPage, NewListing, NewPrice)
@UseGuards(AuthGuard)
@Controller('api/v1/agent/listings')
export class AgentListingAPIController {
  constructor(
    private readonly functionsService: FunctionsService,
    private readonly listingService: ListingService,
    private readonly neighbourhoodService: NeighbourhoodService,
    @InjectRepository(Listing) private readonly listingRepository: EntityRepository<Listing>,
    @InjectRepository(Neighbourhood) private readonly neighbourhoodRepository: EntityRepository<Neighbourhood>,
    @InjectRepository(PriceChange) private readonly priceChangeRepository: EntityRepository<PriceChange>,
  ) {}

  @Providers('identity', 'test_auth')
  @PrincipalTypes('human')
  @Roles('agent')
  @ApiBearerAuth()
  @Get('')
  async listListings(
    @Query('skip', new RejectRepeatedPipe("skip"), new DefaultValuePipe(0), new ParseIntPipe({ exceptionFactory: () => paramFailure("query", "skip", "invalid") }), new IntRangePipe(0, null, "query", "skip")) skip: number,
    @Query('limit', new RejectRepeatedPipe("limit"), new DefaultValuePipe(20), new ParseIntPipe({ exceptionFactory: () => paramFailure("query", "limit", "invalid") }), new IntRangePipe(1, 100, "query", "limit")) limit: number,
    @Query('title', new RejectRepeatedPipe("title"), new ValueRulePipe((value: unknown): boolean => (typeof value === 'string') && Array.from(value as string).length <= 200, "query", "title")) title: string | null = null,
    @Query('neighbourhoodName', new RejectRepeatedPipe("neighbourhoodName"), new ValueRulePipe((value: unknown): boolean => (typeof value === 'string') && Array.from(value as string).length <= 120, "query", "neighbourhoodName")) neighbourhoodName: string | null = null,
    @Query('kind', new RejectRepeatedPipe("kind"), new CoerceStringEnumPipe(PropertyKind, true, "query", "kind")) kind: PropertyKind | null = null,
    @Query('status', new RejectRepeatedPipe("status"), new CoerceStringEnumPipe(ListingStatus, true, "query", "status")) status: ListingStatus | null = null,
    @Query('agentName', new RejectRepeatedPipe("agentName"), new ValueRulePipe((value: unknown): boolean => (typeof value === 'string') && Array.from(value as string).length <= 200, "query", "agentName")) agentName: string | null = null,
  ): Promise<Page<Listing>> {
    return projectResponse(await (async (): Promise<Page<Listing>> => {
      const page = Object.assign(new PageRequest(), { offset: skip, limit: limit });
      return this.listingService.findAll(page, title, neighbourhoodName, kind, status, agentName);
    })(), { kind: 'page', of: { kind: 'entity', entity: 'Listing' } });
  }

  @Providers('identity', 'test_auth')
  @PrincipalTypes('human')
  @Roles('agent')
  @ApiBearerAuth()
  @Get('neighbourhoods')
  async listNeighbourhoods(
    @Query('skip', new RejectRepeatedPipe("skip"), new DefaultValuePipe(0), new ParseIntPipe({ exceptionFactory: () => paramFailure("query", "skip", "invalid") }), new IntRangePipe(0, null, "query", "skip")) skip: number,
    @Query('limit', new RejectRepeatedPipe("limit"), new DefaultValuePipe(20), new ParseIntPipe({ exceptionFactory: () => paramFailure("query", "limit", "invalid") }), new IntRangePipe(1, 100, "query", "limit")) limit: number,
  ): Promise<Page<Neighbourhood>> {
    return projectResponse(await (async (): Promise<Page<Neighbourhood>> => {
      const page = Object.assign(new PageRequest(), { offset: skip, limit: limit });
      return this.neighbourhoodService.findAll(page);
    })(), { kind: 'page', of: { kind: 'entity', entity: 'Neighbourhood' } });
  }

  @Providers('identity', 'test_auth')
  @PrincipalTypes('human')
  @Roles('agent')
  @ApiBearerAuth()
  @Post('new')
  @HttpCode(HttpStatus.CREATED)
  async postNew(
    @RequestBody("object") body: NewListing,
    @Req() req: Request,
  ): Promise<Listing> {
    return projectResponse(await (async (): Promise<Listing> => {
      const place = await this.neighbourhoodRepository.findOne({ id: body.neighbourhoodId });
      if (!place) {
        throw new NotFoundException("Not found");
      }
      const entity = this.listingRepository.create({ title: body.title, neighbourhoodName: place.name, city: place.city, latitude: place.latitude, longitude: place.longitude, kind: body.kind, price: body.price, bedrooms: body.bedrooms, bathrooms: body.bathrooms, areaSqm: body.areaSqm, summary: body.summary, agentName: String(((((req.user ?? (() => { throw new UnauthorizedException({ type: 'about:blank', title: 'Unauthorized', status: 401 }); })()).identity.fullName ?? null) as string | null) ?? ((req.user ?? (() => { throw new UnauthorizedException({ type: 'about:blank', title: 'Unauthorized', status: 401 }); })()).identity.email as string))), agentEmail: ((req.user ?? (() => { throw new UnauthorizedException({ type: 'about:blank', title: 'Unauthorized', status: 401 }); })()).identity.email as string) } as never);
      await this.listingRepository.getEntityManager().persistAndFlush(entity);
      return entity
    })(), { kind: 'entity', entity: 'Listing' });
  }

  @Providers('identity', 'test_auth')
  @PrincipalTypes('human')
  @Roles('agent')
  @ApiBearerAuth()
  @Post('price')
  @HttpCode(HttpStatus.CREATED)
  async postPrice(
    @RequestBody("object") body: NewPrice,
  ): Promise<Listing> {
    return projectResponse(await (async (): Promise<Listing> => {
      const listing: Listing = await this.functionsService.ownListing(body.listingId);
      if (_decimalEquals(listing.price, body.price)) {
        throw new SamePriceError({});
      }
      const oldPrice: DecimalString = listing.price;
      listing.price = body.price;
      await this.listingRepository.getEntityManager().persistAndFlush(listing);
      const entity = this.priceChangeRepository.create({ listingId: listing.id, oldPrice: oldPrice, newPrice: body.price } as never);
      await this.priceChangeRepository.getEntityManager().persistAndFlush(entity);
      await getMqProducer().publishListingPriceChanged({ listingId: listing.id, title: listing.title, oldPrice: oldPrice, newPrice: body.price });
      return listing;
    })(), { kind: 'entity', entity: 'Listing' });
  }

  @Providers('identity', 'test_auth')
  @PrincipalTypes('human')
  @Roles('agent')
  @ApiBearerAuth()
  @Get('summary')
  @ApiResponse({ status: 200, type: AgentSummary })
  async getSummary(
    @Req() req: Request,
  ): Promise<AgentSummary> {
    const me: string = String(((req.user ?? (() => { throw new UnauthorizedException({ type: 'about:blank', title: 'Unauthorized', status: 401 }); })()).identity.email as string));
    return Object.assign(new AgentSummary(), { onTheMarket: await (this.listingRepository.getEntityManager() as SqlEntityManager).createQueryBuilder(Listing, 'e_listing').select('*').where('e_listing.agent_email = ?', [me]).andWhere({ status: ListingStatus.Active }).getCount(), drafts: await (this.listingRepository.getEntityManager() as SqlEntityManager).createQueryBuilder(Listing, 'e_listing').select('*').where('e_listing.agent_email = ?', [me]).andWhere({ status: ListingStatus.Draft }).getCount(), underOffer: await (this.listingRepository.getEntityManager() as SqlEntityManager).createQueryBuilder(Listing, 'e_listing').select('*').where('e_listing.agent_email = ?', [me]).andWhere({ status: ListingStatus.UnderOffer }).getCount(), sold: await (this.listingRepository.getEntityManager() as SqlEntityManager).createQueryBuilder(Listing, 'e_listing').select('*').where('e_listing.agent_email = ?', [me]).andWhere({ status: ListingStatus.Sold }).getCount() });
  }

  @Providers('identity', 'test_auth')
  @PrincipalTypes('human')
  @Roles('agent')
  @ApiBearerAuth()
  @Post('withdraw/:id')
  @HttpCode(HttpStatus.CREATED)
  async postWithdrawById(
    @Param('id', new ParseUUIDPipe({ exceptionFactory: () => paramFailure("path", "id", "invalid") })) id: string,
  ): Promise<Listing> {
    return projectResponse(await (async (): Promise<Listing> => {
      const listing: Listing = await this.functionsService.ownListing(id);
      if ((listing.status !== ListingStatus.Active)) {
        throw new WrongStepError({});
      }
      listing.status = ListingStatus.Withdrawn;
      await this.listingRepository.getEntityManager().persistAndFlush(listing);
      return listing;
    })(), { kind: 'entity', entity: 'Listing' });
  }

  @Providers('identity', 'test_auth')
  @PrincipalTypes('human')
  @Roles('agent')
  @ApiBearerAuth()
  @Post('publish/:id')
  @HttpCode(HttpStatus.CREATED)
  async postPublishById(
    @Param('id', new ParseUUIDPipe({ exceptionFactory: () => paramFailure("path", "id", "invalid") })) id: string,
  ): Promise<Listing> {
    return projectResponse(await (async (): Promise<Listing> => {
      const listing: Listing = await this.functionsService.ownListing(id);
      if (((listing.status !== ListingStatus.Draft) && (listing.status !== ListingStatus.Withdrawn))) {
        throw new WrongStepError({});
      }
      listing.status = ListingStatus.Active;
      listing.publishedAt = new Date();
      await this.listingRepository.getEntityManager().persistAndFlush(listing);
      return listing;
    })(), { kind: 'entity', entity: 'Listing' });
  }

  @Providers('identity', 'test_auth')
  @PrincipalTypes('human')
  @Roles('agent')
  @ApiBearerAuth()
  @Get('page/:id')
  @ApiResponse({ status: 200, type: ListingPage })
  async getPageById(
    @Param('id', new ParseUUIDPipe({ exceptionFactory: () => paramFailure("path", "id", "invalid") })) id: string,
  ): Promise<ListingPage> {
    return await this.functionsService.pageOf(await this.functionsService.ownListing(id));
  }

}
