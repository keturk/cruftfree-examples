import {
  Controller,
  Get,
  Param,
  Query,
  ParseUUIDPipe,
  HttpCode,
  HttpStatus,
  UseGuards,
} from '@nestjs/common';
import { AuthGuard } from '../auth/auth.guard';
import { Public } from '../auth/public.decorator';
import { RequiredPipe } from '../pipes/required.pipe';
import { RejectRepeatedPipe, paramFailure } from '../common/request-validation';
import { InjectRepository } from '@mikro-orm/nestjs';
import { EntityRepository } from '@mikro-orm/core';
import { FunctionsService } from '../functions';
import { GeoPoint } from '../dto/geo-point.struct';
import { HomePin } from '../dto/home-pin.struct';
import { ListingCard } from '../dto/listing-card.struct';
import { ListingPage } from '../dto/listing-page.struct';
import { ListingStatus } from '../enums/listing-status.enum';
import { Listing } from '../realestate_listing_service/entities/listing_db/listing.entity';
import { NotFoundException } from '@nestjs/common';
import { NotPublicError } from '../errors/domain-errors';
import { SqlEntityManager } from '@mikro-orm/postgresql';
import { cardOf } from '../functions';
import { ApiExtraModels, ApiResponse } from '@nestjs/swagger';

@ApiExtraModels(GeoPoint, HomePin, ListingCard, ListingPage)
@UseGuards(AuthGuard)
@Controller('api/v1/homes')
export class HomesAPIController {
  constructor(
    private readonly functionsService: FunctionsService,
    @InjectRepository(Listing) private readonly listingRepository: EntityRepository<Listing>,
  ) {}

  @Public()
  @Get('')
  @ApiResponse({ status: 200, type: [ListingCard] })
  async getEndpoint(
  ): Promise<ListingCard[]> {
    const listings: Listing[] = await (this.listingRepository.getEntityManager() as SqlEntityManager).createQueryBuilder(Listing, 'e_listing').select('*').andWhere({ status: ListingStatus.Active }).orderBy({ 'e_listing.published_at': 'DESC' }).limit(60).getResultList();
    return await Promise.all(listings.map(async (l) => await cardOf(l)));
  }

  @Public()
  @Get('pins')
  @ApiResponse({ status: 200, type: [HomePin] })
  async getPins(
  ): Promise<HomePin[]> {
    const listings: Listing[] = await (this.listingRepository.getEntityManager() as SqlEntityManager).createQueryBuilder(Listing, 'e_listing').select('*').andWhere({ status: ListingStatus.Active }).limit(200).getResultList();
    return listings.map((l) => Object.assign(new HomePin(), { id: l.id, title: l.title, point: Object.assign(new GeoPoint(), { latitude: l.latitude, longitude: l.longitude }) }));
  }

  @Public()
  @Get('search')
  @ApiResponse({ status: 200, type: [ListingCard] })
  async getSearch(
    @Query('q', new RejectRepeatedPipe("q"), new RequiredPipe("query", "q")) q: string,
  ): Promise<ListingCard[]> {
    const listings: Listing[] = await (this.listingRepository.getEntityManager() as SqlEntityManager).createQueryBuilder(Listing, 'e_listing').select('*').andWhere({ status: ListingStatus.Active }).where(`to_tsvector('english', coalesce(e_listing.title, '') || ' ' || coalesce(e_listing.summary, '') || ' ' || coalesce(e_listing.neighbourhood_name, '')) @@ plainto_tsquery('english', ?)`, [String(q)]).limit(60).getResultList();
    return await Promise.all(listings.map(async (l) => await cardOf(l)));
  }

  @Public()
  @Get('home/:id')
  @ApiResponse({ status: 200, type: ListingPage })
  async getHomeById(
    @Param('id', new ParseUUIDPipe({ exceptionFactory: () => paramFailure("path", "id", "invalid") })) id: string,
  ): Promise<ListingPage> {
    const listing = await this.listingRepository.findOne({ id: id });
    if (!listing) {
      throw new NotFoundException("Not found");
    }
    if (((listing.status === ListingStatus.Draft) || (listing.status === ListingStatus.Withdrawn))) {
      throw new NotPublicError({});
    }
    return await this.functionsService.pageOf(listing);
  }

}
