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
import { EntityManager } from '@mikro-orm/core';
import { InjectRepository } from '@mikro-orm/nestjs';
import { EntityRepository } from '@mikro-orm/core';
import { FunctionsService } from '../functions';
import { OfferService } from '../services/offer.service';
import { ContractService } from '../services/contract.service';
import { ContractStatus } from '../enums/contract-status.enum';
import { DealSummary } from '../dto/deal-summary.struct';
import { Financing } from '../enums/financing.enum';
import { OfferStatus } from '../enums/offer-status.enum';
import { Page } from '../dto/page';
import { PageRequest } from '../dto/page-request.struct';
import { Contract } from '../realestate_deal_service/entities/deal_db/contract.entity';
import { Offer } from '../realestate_deal_service/entities/deal_db/offer.entity';
import { LockMode } from '@mikro-orm/core';
import { NotFoundException } from '@nestjs/common';
import { UnauthorizedException } from '@nestjs/common';
import { SqlEntityManager } from '@mikro-orm/postgresql';
import { WrongStepError } from '../errors/domain-errors';
import { _decimalAdd } from '../realestate_deal_service/_decimalHelpers';
import { _decimalOf } from '../realestate_deal_service/_decimalHelpers';
import { projectResponse } from '../support/responseProjection';
import { realestateListingServiceClient } from '../clients/realestate-listing-service-client.service';
import { sendMail } from '../functions';
import { transactionUnit } from '../transactionUnit';
import { ApiExtraModels, ApiResponse, ApiBearerAuth } from '@nestjs/swagger';

@ApiExtraModels(DealSummary)
@UseGuards(AuthGuard)
@Controller('api/v1/agent/deals')
export class AgentDealAPIController {
  constructor(
    private readonly functionsService: FunctionsService,
    private readonly offerService: OfferService,
    private readonly contractService: ContractService,
    @InjectRepository(Contract) private readonly contractRepository: EntityRepository<Contract>,
    @InjectRepository(Offer) private readonly offerRepository: EntityRepository<Offer>,
    private readonly dealDbEm: EntityManager,
  ) {}

  @Providers('identity')
  @PrincipalTypes('human')
  @Roles('agent')
  @ApiBearerAuth()
  @Get('contracts')
  async listContracts(
    @Query('skip', new RejectRepeatedPipe("skip"), new DefaultValuePipe(0), new ParseIntPipe({ exceptionFactory: () => paramFailure("query", "skip", "invalid") }), new IntRangePipe(0, null, "query", "skip")) skip: number,
    @Query('limit', new RejectRepeatedPipe("limit"), new DefaultValuePipe(20), new ParseIntPipe({ exceptionFactory: () => paramFailure("query", "limit", "invalid") }), new IntRangePipe(1, 100, "query", "limit")) limit: number,
    @Query('listingTitle', new RejectRepeatedPipe("listingTitle"), new ValueRulePipe((value: unknown): boolean => (typeof value === 'string') && Array.from(value as string).length <= 200, "query", "listingTitle")) listingTitle: string | null = null,
    @Query('buyerName', new RejectRepeatedPipe("buyerName"), new ValueRulePipe((value: unknown): boolean => (typeof value === 'string') && Array.from(value as string).length <= 200, "query", "buyerName")) buyerName: string | null = null,
    @Query('status', new RejectRepeatedPipe("status"), new CoerceStringEnumPipe(ContractStatus, true, "query", "status")) status: ContractStatus | null = null,
  ): Promise<Page<Contract>> {
    return projectResponse(await (async (): Promise<Page<Contract>> => {
      const page = Object.assign(new PageRequest(), { offset: skip, limit: limit });
      return this.contractService.findAll(page, listingTitle, buyerName, status);
    })(), { kind: 'page', of: { kind: 'entity', entity: 'Contract' } });
  }

  @Providers('identity')
  @PrincipalTypes('human')
  @Roles('agent')
  @ApiBearerAuth()
  @Get('offers')
  async listOffers(
    @Query('skip', new RejectRepeatedPipe("skip"), new DefaultValuePipe(0), new ParseIntPipe({ exceptionFactory: () => paramFailure("query", "skip", "invalid") }), new IntRangePipe(0, null, "query", "skip")) skip: number,
    @Query('limit', new RejectRepeatedPipe("limit"), new DefaultValuePipe(20), new ParseIntPipe({ exceptionFactory: () => paramFailure("query", "limit", "invalid") }), new IntRangePipe(1, 100, "query", "limit")) limit: number,
    @Query('listingTitle', new RejectRepeatedPipe("listingTitle"), new ValueRulePipe((value: unknown): boolean => (typeof value === 'string') && Array.from(value as string).length <= 200, "query", "listingTitle")) listingTitle: string | null = null,
    @Query('buyerName', new RejectRepeatedPipe("buyerName"), new ValueRulePipe((value: unknown): boolean => (typeof value === 'string') && Array.from(value as string).length <= 200, "query", "buyerName")) buyerName: string | null = null,
    @Query('financing', new RejectRepeatedPipe("financing"), new CoerceStringEnumPipe(Financing, true, "query", "financing")) financing: Financing | null = null,
    @Query('status', new RejectRepeatedPipe("status"), new CoerceStringEnumPipe(OfferStatus, true, "query", "status")) status: OfferStatus | null = null,
  ): Promise<Page<Offer>> {
    return projectResponse(await (async (): Promise<Page<Offer>> => {
      const page = Object.assign(new PageRequest(), { offset: skip, limit: limit });
      return this.offerService.findAll(page, listingTitle, buyerName, financing, status);
    })(), { kind: 'page', of: { kind: 'entity', entity: 'Offer' } });
  }

  @Providers('identity')
  @PrincipalTypes('human')
  @Roles('agent')
  @ApiBearerAuth()
  @Get('summary')
  @ApiResponse({ status: 200, type: DealSummary })
  async getSummary(
    @Req() req: Request,
  ): Promise<DealSummary> {
    const me: string = String(((req.user ?? (() => { throw new UnauthorizedException({ type: 'about:blank', title: 'Unauthorized', status: 401 }); })()).identity.email as string));
    const signed: Contract[] = await (this.contractRepository.getEntityManager() as SqlEntityManager).createQueryBuilder(Contract, 'e_contract').select('*').where('e_contract.agent_email = ?', [me]).andWhere({ status: ContractStatus.Signed }).limit(500).getResultList();
    let signedValue: DecimalString = _decimalOf('0');
    for (const contract of signed) {
      signedValue = _decimalAdd(signedValue, contract.price);
    }
    return Object.assign(new DealSummary(), { offersWaiting: await (this.offerRepository.getEntityManager() as SqlEntityManager).createQueryBuilder(Offer, 'e_offer').select('*').where('e_offer.agent_email = ?', [me]).andWhere({ status: OfferStatus.Submitted }).getCount(), contractsOut: await (this.contractRepository.getEntityManager() as SqlEntityManager).createQueryBuilder(Contract, 'e_contract').select('*').where('e_contract.agent_email = ?', [me]).andWhere({ status: ContractStatus.AwaitingSignature }).getCount(), signed: signed.length, signedValue: signedValue });
  }

  // The lock is on every open offer for the home, so a second agent's click finds them decided.
  @Providers('identity')
  @PrincipalTypes('human')
  @Roles('agent')
  @ApiBearerAuth()
  @Post('accept/:id')
  @HttpCode(HttpStatus.CREATED)
  async postAcceptById(
    @Param('id', new ParseUUIDPipe({ exceptionFactory: () => paramFailure("path", "id", "invalid") })) id: string,
  ): Promise<Contract> {
    return projectResponse(await (async (): Promise<Contract> => {
      const chosen: Offer = await this.functionsService.ownAsAgent(id);
      await transactionUnit(this.dealDbEm, async (manager: EntityManager) => {
        const open: Offer[] = await (this.offerRepository.getEntityManager() as SqlEntityManager).createQueryBuilder(Offer, 'e_offer').select('*').where('e_offer.listing_id = ?', [chosen.listingId]).andWhere({ status: OfferStatus.Submitted }).setLockMode(LockMode.PESSIMISTIC_WRITE).getResultList();
        const locked = await (this.offerRepository.getEntityManager() as SqlEntityManager).createQueryBuilder(Offer, 'e_offer').select('*').where('e_offer.id = ?', [id]).setLockMode(LockMode.PESSIMISTIC_WRITE).getSingleResult();
        if (!locked) {
          throw new NotFoundException("Not found");
        }
        if ((locked.status !== OfferStatus.Submitted)) {
          throw new WrongStepError({});
        }
        for (const other of open) {
          other.status = ((other.id === id) ? OfferStatus.Accepted : OfferStatus.Rejected);
          await this.offerRepository.getEntityManager().persistAndFlush(other);
        }
        const entity = this.contractRepository.create({ listingId: locked.listingId, listingTitle: locked.listingTitle, offerId: locked.id, buyerName: locked.buyerName, buyerEmail: locked.buyerEmail, agentEmail: locked.agentEmail, price: locked.amount } as never);
        await this.contractRepository.getEntityManager().persistAndFlush(entity);
      });
      (await realestateListingServiceClient().post('/internal/listings/under-offer', { data: {listingId: chosen.listingId} }, false)).data;
      const contract = await (this.contractRepository.getEntityManager() as SqlEntityManager).createQueryBuilder(Contract, 'e_contract').select('*').where('e_contract.offer_id = ?', [id]).getSingleResult();
      if (!contract) {
        throw new NotFoundException("Not found");
      }
      await this.functionsService.sendForSignature(contract);
      await sendMail(String(chosen.buyerEmail), `Your offer on ${chosen.listingTitle} was accepted`, 'The contract is on its way for you to sign.', `accepted-${id}`);
      return contract;
    })(), { kind: 'entity', entity: 'Contract' });
  }

  @Providers('identity')
  @PrincipalTypes('human')
  @Roles('agent')
  @ApiBearerAuth()
  @Post('reject/:id')
  @HttpCode(HttpStatus.CREATED)
  async postRejectById(
    @Param('id', new ParseUUIDPipe({ exceptionFactory: () => paramFailure("path", "id", "invalid") })) id: string,
  ): Promise<Offer> {
    return projectResponse(await (async (): Promise<Offer> => {
      const offer: Offer = await this.functionsService.ownAsAgent(id);
      if ((offer.status !== OfferStatus.Submitted)) {
        throw new WrongStepError({});
      }
      offer.status = OfferStatus.Rejected;
      await this.offerRepository.getEntityManager().persistAndFlush(offer);
      await sendMail(String(offer.buyerEmail), `Your offer on ${offer.listingTitle}`, 'The seller has decided not to accept it.', `rejected-${id}`);
      return offer;
    })(), { kind: 'entity', entity: 'Offer' });
  }

}
