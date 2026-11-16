import {
  Controller,
  Get,
  Post,
  Param,
  ParseUUIDPipe,
  HttpCode,
  HttpStatus,
  UseGuards,
} from '@nestjs/common';
import { AuthGuard } from '../auth/auth.guard';
import { PrincipalTypes } from '../auth/optional-auth.decorator';
import { Providers } from '../auth/providers.decorator';
import { RequestBody, paramFailure } from '../common/request-validation';
import { InjectRepository } from '@mikro-orm/nestjs';
import { EntityRepository } from '@mikro-orm/core';
import { ListingCard } from '../dto/listing-card.struct';
import { ListingFacts } from '../dto/listing-facts.struct';
import { ListingNotice } from '../dto/listing-notice.struct';
import { ListingStatus } from '../enums/listing-status.enum';
import { Listing } from '../realestate_listing_service/entities/listing_db/listing.entity';
import { NotFoundException } from '@nestjs/common';
import { cardOf } from '../functions';
import { ApiExtraModels, ApiResponse, ApiBearerAuth } from '@nestjs/swagger';

@ApiExtraModels(ListingCard, ListingFacts, ListingNotice)
@UseGuards(AuthGuard)
@Controller('internal/listings')
export class ListingInternalAPIController {
  constructor(
    @InjectRepository(Listing) private readonly listingRepository: EntityRepository<Listing>,
  ) {}

  @Providers('machine')
  @PrincipalTypes('machine')
  @ApiBearerAuth()
  @Post('reopen')
  @HttpCode(HttpStatus.CREATED)
  @ApiResponse({ status: 201, type: ListingCard })
  async postReopen(
    @RequestBody("object") body: ListingNotice,
  ): Promise<ListingCard> {
    const listing = await this.listingRepository.findOne({ id: body.listingId });
    if (!listing) {
      throw new NotFoundException("Not found");
    }
    listing.status = ListingStatus.Active;
    await this.listingRepository.getEntityManager().persistAndFlush(listing);
    return await cardOf(listing);
  }

  @Providers('machine')
  @PrincipalTypes('machine')
  @ApiBearerAuth()
  @Post('sold')
  @HttpCode(HttpStatus.CREATED)
  @ApiResponse({ status: 201, type: ListingCard })
  async postSold(
    @RequestBody("object") body: ListingNotice,
  ): Promise<ListingCard> {
    const listing = await this.listingRepository.findOne({ id: body.listingId });
    if (!listing) {
      throw new NotFoundException("Not found");
    }
    listing.status = ListingStatus.Sold;
    await this.listingRepository.getEntityManager().persistAndFlush(listing);
    return await cardOf(listing);
  }

  @Providers('machine')
  @PrincipalTypes('machine')
  @ApiBearerAuth()
  @Post('under-offer')
  @HttpCode(HttpStatus.CREATED)
  @ApiResponse({ status: 201, type: ListingCard })
  async postUnderOffer(
    @RequestBody("object") body: ListingNotice,
  ): Promise<ListingCard> {
    const listing = await this.listingRepository.findOne({ id: body.listingId });
    if (!listing) {
      throw new NotFoundException("Not found");
    }
    listing.status = ListingStatus.UnderOffer;
    await this.listingRepository.getEntityManager().persistAndFlush(listing);
    return await cardOf(listing);
  }

  @Providers('machine')
  @PrincipalTypes('machine')
  @ApiBearerAuth()
  @Get('facts/:id')
  @ApiResponse({ status: 200, type: ListingFacts })
  async getFactsById(
    @Param('id', new ParseUUIDPipe({ exceptionFactory: () => paramFailure("path", "id", "invalid") })) id: string,
  ): Promise<ListingFacts> {
    const listing = await this.listingRepository.findOne({ id: id });
    if (!listing) {
      throw new NotFoundException("Not found");
    }
    return Object.assign(new ListingFacts(), { title: listing.title, status: listing.status, price: listing.price, agentName: listing.agentName, agentEmail: listing.agentEmail });
  }

}
