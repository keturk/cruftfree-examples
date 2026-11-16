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
import { OfferService } from '../services/offer.service';
import { ContractService } from '../services/contract.service';
import { Financing } from '../enums/financing.enum';
import { ListingStatus } from '../enums/listing-status.enum';
import { MakeOffer } from '../dto/make-offer.struct';
import { OfferStatus } from '../enums/offer-status.enum';
import { Contract } from '../realestate_deal_service/entities/deal_db/contract.entity';
import { Offer } from '../realestate_deal_service/entities/deal_db/offer.entity';
import { AlreadyOfferedError } from '../errors/domain-errors';
import { NotOnTheMarketError } from '../errors/domain-errors';
import { NotYourOfferError } from '../errors/domain-errors';
import { WrongStepError } from '../errors/domain-errors';
import { ListingServiceListingFactsResponse } from '../clients/realestate-listing-service-responses';
import { SqlEntityManager } from '@mikro-orm/postgresql';
import { UnauthorizedException } from '@nestjs/common';
import { _decimalText } from '../realestate_deal_service/_decimalHelpers';
import { lenderReferenceFor } from '../functions';
import { sendMail } from '../functions';
import { projectResponse } from '../support/responseProjection';
import { realestateListingServiceClient } from '../clients/realestate-listing-service-client.service';
import { ApiExtraModels, ApiBearerAuth } from '@nestjs/swagger';

@ApiExtraModels(MakeOffer)
@UseGuards(AuthGuard)
@Controller('api/v1/offers')
export class BuyerDealAPIController {
  constructor(
    private readonly offerService: OfferService,
    private readonly contractService: ContractService,
    @InjectRepository(Contract) private readonly contractRepository: EntityRepository<Contract>,
    @InjectRepository(Offer) private readonly offerRepository: EntityRepository<Offer>,
  ) {}

  @Providers('identity', 'test_auth')
  @PrincipalTypes('human')
  @ApiBearerAuth()
  @Post('make')
  @HttpCode(HttpStatus.CREATED)
  async postMake(
    @RequestBody("object") body: MakeOffer,
    @Req() req: Request,
  ): Promise<Offer> {
    return projectResponse(await (async (): Promise<Offer> => {
      const buyerEmail: string = String(((req.user ?? (() => { throw new UnauthorizedException({ type: 'about:blank', title: 'Unauthorized', status: 401 }); })()).identity.email as string));
      const buyerName: string = String(((((req.user ?? (() => { throw new UnauthorizedException({ type: 'about:blank', title: 'Unauthorized', status: 401 }); })()).identity.fullName ?? null) as string | null) ?? ((req.user ?? (() => { throw new UnauthorizedException({ type: 'about:blank', title: 'Unauthorized', status: 401 }); })()).identity.email as string)));
      const listing: ListingServiceListingFactsResponse = (await realestateListingServiceClient().get(`/internal/listings/facts/${body.listingId}`, {}, false)).data;
      if ((listing['status'] !== ListingStatus.Active)) {
        throw new NotOnTheMarketError({});
      }
      if (((await (this.offerRepository.getEntityManager() as SqlEntityManager).createQueryBuilder(Offer, 'e_offer').select('*').where('e_offer.listing_id = ?', [body.listingId]).andWhere('e_offer.buyer_email = ?', [buyerEmail]).andWhere({ status: OfferStatus.Submitted }).limit(1).getResultList())[0] ?? null != null)) {
        throw new AlreadyOfferedError({});
      }
      const lenderReference: string | null = ((body.financing === Financing.Mortgage) ? await lenderReferenceFor(body, buyerName, buyerEmail) : null);
      const created = this.offerRepository.create({ listingId: body.listingId, listingTitle: listing['title'], buyerName: buyerName, buyerEmail: buyerEmail, agentEmail: listing['agentEmail'], amount: body.amount, financing: body.financing, lenderReference: lenderReference } as never);
      await this.offerRepository.getEntityManager().persistAndFlush(created);
      await sendMail(String(listing['agentEmail']), `New offer on ${listing['title']}`, `${buyerName} has offered $${_decimalText(body.amount)}.`, `offer-${created.id}`);
      return created;
    })(), { kind: 'entity', entity: 'Offer' });
  }

  @Providers('identity', 'test_auth')
  @PrincipalTypes('human')
  @ApiBearerAuth()
  @Get('mine')
  async getMine(
    @Req() req: Request,
  ): Promise<Offer[]> {
    return projectResponse(await (async (): Promise<Offer[]> => {
      return await (this.offerRepository.getEntityManager() as SqlEntityManager).createQueryBuilder(Offer, 'e_offer').select('*').where('e_offer.buyer_email = ?', [((req.user ?? (() => { throw new UnauthorizedException({ type: 'about:blank', title: 'Unauthorized', status: 401 }); })()).identity.email as string)]).orderBy({ 'e_offer.created_at': 'DESC' }).limit(50).getResultList();
    })(), { kind: 'list', of: { kind: 'entity', entity: 'Offer' } });
  }

  @Providers('identity', 'test_auth')
  @PrincipalTypes('human')
  @ApiBearerAuth()
  @Get('my-contracts')
  async getMyContracts(
    @Req() req: Request,
  ): Promise<Contract[]> {
    return projectResponse(await (async (): Promise<Contract[]> => {
      return await (this.contractRepository.getEntityManager() as SqlEntityManager).createQueryBuilder(Contract, 'e_contract').select('*').where('e_contract.buyer_email = ?', [((req.user ?? (() => { throw new UnauthorizedException({ type: 'about:blank', title: 'Unauthorized', status: 401 }); })()).identity.email as string)]).orderBy({ 'e_contract.created_at': 'DESC' }).limit(20).getResultList();
    })(), { kind: 'list', of: { kind: 'entity', entity: 'Contract' } });
  }

  @Providers('identity', 'test_auth')
  @PrincipalTypes('human')
  @ApiBearerAuth()
  @Post('withdraw/:id')
  @HttpCode(HttpStatus.CREATED)
  async postWithdrawById(
    @Param('id', new ParseUUIDPipe({ exceptionFactory: () => paramFailure("path", "id", "invalid") })) id: string,
    @Req() req: Request,
  ): Promise<Offer> {
    return projectResponse(await (async (): Promise<Offer> => {
      const offer: Offer | null = (await (this.offerRepository.getEntityManager() as SqlEntityManager).createQueryBuilder(Offer, 'e_offer').select('*').where('e_offer.id = ?', [id]).andWhere('e_offer.buyer_email = ?', [((req.user ?? (() => { throw new UnauthorizedException({ type: 'about:blank', title: 'Unauthorized', status: 401 }); })()).identity.email as string)]).limit(1).getResultList())[0] ?? null;
      if ((offer == null)) {
        throw new NotYourOfferError({});
      }
      if ((offer.status !== OfferStatus.Submitted)) {
        throw new WrongStepError({});
      }
      offer.status = OfferStatus.Withdrawn;
      await this.offerRepository.getEntityManager().persistAndFlush(offer);
      return offer;
    })(), { kind: 'entity', entity: 'Offer' });
  }

}
