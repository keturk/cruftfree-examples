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
import { Public } from '../auth/public.decorator';
import { PrincipalTypes } from '../auth/optional-auth.decorator';
import { Providers } from '../auth/providers.decorator';
import { RequestBody, paramFailure } from '../common/request-validation';
import { EntityManager } from '@mikro-orm/core';
import { InjectRepository } from '@mikro-orm/nestjs';
import { EntityRepository } from '@mikro-orm/core';
import { FunctionsService } from '../functions';
import { HoldRequest } from '../dto/hold-request.struct';
import { Offer } from '../dto/offer.struct';
import { PayRequest } from '../dto/pay-request.struct';
import { RoomTypeCard } from '../dto/room-type-card.struct';
import { SearchRequest } from '../dto/search-request.struct';
import { StayCard } from '../dto/stay-card.struct';
import { StayStatus } from '../enums/stay-status.enum';
import { TestCard } from '../enums/test-card.enum';
import { RoomType } from '../hotel_stay_service/entities/stay_db/room-type.entity';
import { Stay } from '../hotel_stay_service/entities/stay_db/stay.entity';
import { CannotCancelError } from '../errors/domain-errors';
import { CardDeclinedError } from '../errors/domain-errors';
import { HoldLapsedError } from '../errors/domain-errors';
import { NoSuchRoomTypeError } from '../errors/domain-errors';
import { SoldOutError } from '../errors/domain-errors';
import { TooManyGuestsError } from '../errors/domain-errors';
import { Charge } from '../clients/payment-provider-models';
import { ChargeStatus } from '../clients/payment-provider-models';
import { HOLD_MINUTES } from '../constants';
import { LockMode } from '@mikro-orm/core';
import { NotFoundException } from '@nestjs/common';
import { UnauthorizedException } from '@nestjs/common';
import { PaymentProviderClient } from '../clients/payment-provider-client';
import { SqlEntityManager } from '@mikro-orm/postgresql';
import { _decimalMul } from '../hotel_stay_service/_decimalHelpers';
import { _decimalText } from '../hotel_stay_service/_decimalHelpers';
import { addMinutes } from 'date-fns';
import { differenceInDays } from 'date-fns';
import { format } from 'date-fns';
import { parseISO } from 'date-fns';
import { bufferEvents } from '../eventOutbox';
import { canCancel } from '../functions';
import { cardOf } from '../functions';
import { cardsOf } from '../functions';
import { checkDates } from '../functions';
import { roomTypeCardOf } from '../functions';
import { getProducer as getMqProducer } from '../mq/producer';
import { randomInt } from 'crypto';
import { transactionUnit } from '../transactionUnit';
import { ApiExtraModels, ApiResponse, ApiBearerAuth } from '@nestjs/swagger';

@ApiExtraModels(HoldRequest, Offer, PayRequest, RoomTypeCard, SearchRequest, StayCard)
@UseGuards(AuthGuard)
@Controller('api/v1/stays')
export class StayAPIController {
  constructor(
    private readonly functionsService: FunctionsService,
    @InjectRepository(RoomType) private readonly roomTypeRepository: EntityRepository<RoomType>,
    @InjectRepository(Stay) private readonly stayRepository: EntityRepository<Stay>,
    private readonly stayDbEm: EntityManager,
  ) {}

  // The room type's row is locked for the check and the insert, so the last room goes to one guest.
  @Providers('identity', 'test_auth')
  @PrincipalTypes('human')
  @ApiBearerAuth()
  @Post('hold')
  @HttpCode(HttpStatus.CREATED)
  @ApiResponse({ status: 201, type: StayCard })
  async postHold(
    @RequestBody("object") body: HoldRequest,
    @Req() req: Request,
  ): Promise<StayCard> {
    await checkDates(body.arrival, body.departure);
    const nights: number = differenceInDays(parseISO(body.departure), parseISO(body.arrival));
    const guestName: string = ((((req.user ?? (() => { throw new UnauthorizedException({ type: 'about:blank', title: 'Unauthorized', status: 401 }); })()).identity.fullName ?? null) as string | null) ?? String(((req.user ?? (() => { throw new UnauthorizedException({ type: 'about:blank', title: 'Unauthorized', status: 401 }); })()).identity.email as string)));
    const code: string = `MH-${Array.from({ length: 6 }, () => '0123456789'.charAt(randomInt('0123456789'.length))).join('')}`;
    await bufferEvents(async () => {
      await transactionUnit(this.stayDbEm, async (manager: EntityManager) => {
        const type = await (this.roomTypeRepository.getEntityManager() as SqlEntityManager).createQueryBuilder(RoomType, 'e_room_type').select('*').where('e_room_type.id = ?', [body.roomTypeId]).andWhere('e_room_type.listed = ?', [true]).setLockMode(LockMode.PESSIMISTIC_WRITE).getSingleResult();
        if (!type) {
          throw new NotFoundException("Not found");
        }
        if ((body.guests > type.sleeps)) {
          throw new TooManyGuestsError({});
        }
        if ((await this.functionsService.leftFor(type, body.arrival, body.departure) < 1)) {
          throw new SoldOutError({});
        }
        const entity = this.stayRepository.create({ code: code, roomTypeId: type.id, roomTypeName: type.name, guestId: (req.user ?? (() => { throw new UnauthorizedException({ type: 'about:blank', title: 'Unauthorized', status: 401 }); })()).userId, guestName: guestName, guestEmail: ((req.user ?? (() => { throw new UnauthorizedException({ type: 'about:blank', title: 'Unauthorized', status: 401 }); })()).identity.email as string), arrival: body.arrival, departure: body.departure, nights: nights, guests: body.guests, total: _decimalMul(type.nightlyRate, nights), holdUntil: addMinutes(new Date(), HOLD_MINUTES) } as never);
        await this.stayRepository.getEntityManager().persistAndFlush(entity);
      });
    });
    const held = await (this.stayRepository.getEntityManager() as SqlEntityManager).createQueryBuilder(Stay, 'e_stay').select('*').where('e_stay.code = ?', [code]).getSingleResult();
    if (!held) {
      throw new NotFoundException("Not found");
    }
    return await cardOf(held);
  }

  @Providers('identity', 'test_auth')
  @PrincipalTypes('human')
  @ApiBearerAuth()
  @Get('mine')
  @ApiResponse({ status: 200, type: [StayCard] })
  async getMine(
    @Req() req: Request,
  ): Promise<StayCard[]> {
    return await cardsOf(await (this.stayRepository.getEntityManager() as SqlEntityManager).createQueryBuilder(Stay, 'e_stay').select('*').where('e_stay.guest_id = ?', [(req.user ?? (() => { throw new UnauthorizedException({ type: 'about:blank', title: 'Unauthorized', status: 401 }); })()).userId]).orderBy({ 'e_stay.arrival': 'DESC' }).limit(100).getResultList());
  }

  // Paying twice with the same stay finds the first charge at the vendor, so a retry cannot charge twice.
  @Providers('identity', 'test_auth')
  @PrincipalTypes('human')
  @ApiBearerAuth()
  @Post('pay')
  @HttpCode(HttpStatus.CREATED)
  @ApiResponse({ status: 201, type: StayCard })
  async postPay(
    @RequestBody("object") body: PayRequest,
  ): Promise<StayCard> {
    const stay: Stay = await this.functionsService.ownStay(body.stayId);
    if ((stay.status === StayStatus.Confirmed)) {
      return await cardOf(stay);
    }
    if (((stay.status !== StayStatus.Held) || ((stay.holdUntil ?? new Date()) <= new Date()))) {
      throw new HoldLapsedError({});
    }
    const cardToken: string = ((body.card === TestCard.CardThatIsDeclined) ? 'tok_declined' : 'tok_pays');
    const answer: Charge = await new PaymentProviderClient().createCharge({ cardToken: cardToken, amount: stay.total, currency: 'USD', reference: stay.code, idempotencyKey: `stay-${stay.code}-${cardToken}` });
    if ((answer.status !== ChargeStatus.Succeeded)) {
      throw new CardDeclinedError({});
    }
    stay.chargeId = answer.id;
    stay.status = StayStatus.Confirmed;
    stay.holdUntil = null;
    await this.stayRepository.getEntityManager().persistAndFlush(stay);
    await getMqProducer().publishStayConfirmed({ code: stay.code, guestName: stay.guestName, guestEmail: String(stay.guestEmail), roomTypeName: stay.roomTypeName, arrival: format(parseISO(stay.arrival), 'dd MMMM yyyy'), departure: format(parseISO(stay.departure), 'dd MMMM yyyy'), total: _decimalText(stay.total) });
    return await cardOf(stay);
  }

  @Public()
  @Get('room-types')
  @ApiResponse({ status: 200, type: [RoomTypeCard] })
  async getRoomTypes(
  ): Promise<RoomTypeCard[]> {
    const types: RoomType[] = await (this.roomTypeRepository.getEntityManager() as SqlEntityManager).createQueryBuilder(RoomType, 'e_room_type').select('*').where('e_room_type.listed = ?', [true]).orderBy({ 'e_room_type.nightly_rate': 'ASC' }).limit(50).getResultList();
    const cards: RoomTypeCard[] = [];
    for (const type of types) {
      cards.push(await roomTypeCardOf(type));
    }
    return cards;
  }

  // A read, sent as a body so the dates are typed. It changes nothing and holds nothing.
  @Public()
  @Post('search')
  @HttpCode(HttpStatus.CREATED)
  @ApiResponse({ status: 201, type: [Offer] })
  async postSearch(
    @RequestBody("object") body: SearchRequest,
  ): Promise<Offer[]> {
    await checkDates(body.arrival, body.departure);
    const nights: number = differenceInDays(parseISO(body.departure), parseISO(body.arrival));
    const types: RoomType[] = await (this.roomTypeRepository.getEntityManager() as SqlEntityManager).createQueryBuilder(RoomType, 'e_room_type').select('*').where('e_room_type.listed = ?', [true]).andWhere('e_room_type.sleeps >= ?', [body.guests]).orderBy({ 'e_room_type.nightly_rate': 'ASC' }).limit(50).getResultList();
    const offers: Offer[] = [];
    for (const type of types) {
      const left: number = await this.functionsService.leftFor(type, body.arrival, body.departure);
      if ((left > 0)) {
        offers.push(Object.assign(new Offer(), { roomTypeId: type.id, name: type.name, summary: type.summary, sleeps: type.sleeps, nightlyRate: type.nightlyRate, nights: nights, total: _decimalMul(type.nightlyRate, nights), left: left }));
      }
    }
    return offers;
  }

  @Providers('identity', 'test_auth')
  @PrincipalTypes('human')
  @ApiBearerAuth()
  @Post('mine/:id/cancel')
  @HttpCode(HttpStatus.CREATED)
  @ApiResponse({ status: 201, type: StayCard })
  async postMineByIdCancel(
    @Param('id', new ParseUUIDPipe({ exceptionFactory: () => paramFailure("path", "id", "invalid") })) id: string,
  ): Promise<StayCard> {
    const stay: Stay = await this.functionsService.ownStay(id);
    if ((!await canCancel(stay))) {
      throw new CannotCancelError({});
    }
    await this.functionsService.cancelStay(stay);
    return await cardOf(stay);
  }

  @Public()
  @Get('room-types/:id')
  @ApiResponse({ status: 200, type: RoomTypeCard })
  async getRoomTypesById(
    @Param('id', new ParseUUIDPipe({ exceptionFactory: () => paramFailure("path", "id", "invalid") })) id: string,
  ): Promise<RoomTypeCard> {
    const type: RoomType | null = (await (this.roomTypeRepository.getEntityManager() as SqlEntityManager).createQueryBuilder(RoomType, 'e_room_type').select('*').where('e_room_type.id = ?', [id]).andWhere('e_room_type.listed = ?', [true]).limit(1).getResultList())[0] ?? null;
    if ((type == null)) {
      throw new NoSuchRoomTypeError({});
    }
    return await roomTypeCardOf(type);
  }

  @Providers('identity', 'test_auth')
  @PrincipalTypes('human')
  @ApiBearerAuth()
  @Get('mine/:id')
  @ApiResponse({ status: 200, type: StayCard })
  async getMineById(
    @Param('id', new ParseUUIDPipe({ exceptionFactory: () => paramFailure("path", "id", "invalid") })) id: string,
  ): Promise<StayCard> {
    return await cardOf(await this.functionsService.ownStay(id));
  }

}
