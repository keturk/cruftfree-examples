import {
  Controller,
  Delete,
  Get,
  Post,
  Put,
  Param,
  Query,
  DefaultValuePipe,
  ParseBoolPipe,
  ParseIntPipe,
  ParseUUIDPipe,
  HttpCode,
  HttpStatus,
  UseGuards,
} from '@nestjs/common';
import { AuthGuard } from '../auth/auth.guard';
import { PrincipalTypes } from '../auth/optional-auth.decorator';
import { Roles } from '../auth/roles.decorator';
import { Providers } from '../auth/providers.decorator';
import { RequestBody, RejectRepeatedPipe, paramFailure } from '../common/request-validation';
import { CoerceStringEnumPipe } from '../pipes/string-enum-query.pipe';
import { IntRangePipe } from '../pipes/int-range.pipe';
import { ValueRulePipe } from '../pipes/value-rule.pipe';
import { EntityManager } from '@mikro-orm/core';
import { InjectRepository } from '@mikro-orm/nestjs';
import { EntityRepository } from '@mikro-orm/core';
import { FunctionsService } from '../functions';
import { RoomTypeService } from '../services/room_type.service';
import { StayService } from '../services/stay.service';
import { AssignRequest } from '../dto/assign-request.struct';
import { CalendarStay } from '../dto/calendar-stay.struct';
import { ConditionRequest } from '../dto/condition-request.struct';
import { CreateRoomTypeDto } from '../dto/create-room-type.dto';
import { DeskStay } from '../dto/desk-stay.struct';
import { DeskSummary } from '../dto/desk-summary.struct';
import { NoteRequest } from '../dto/note-request.struct';
import { OccupancyPoint } from '../dto/occupancy-point.struct';
import { Page } from '../dto/page';
import { PageRequest } from '../dto/page-request.struct';
import { RoomCard } from '../dto/room-card.struct';
import { RoomCondition } from '../enums/room-condition.enum';
import { StayCard } from '../dto/stay-card.struct';
import { StayStatus } from '../enums/stay-status.enum';
import { UpdateRoomTypeDto } from '../dto/update-room-type.dto';
import { Room } from '../hotel_stay_service/entities/stay_db/room.entity';
import { RoomType } from '../hotel_stay_service/entities/stay_db/room-type.entity';
import { Stay } from '../hotel_stay_service/entities/stay_db/stay.entity';
import { BadMoveError } from '../errors/domain-errors';
import { CannotCancelError } from '../errors/domain-errors';
import { RoomNotReadyError } from '../errors/domain-errors';
import { RoomOccupiedError } from '../errors/domain-errors';
import { LockMode } from '@mikro-orm/core';
import { NotFoundException } from '@nestjs/common';
import { SqlEntityManager } from '@mikro-orm/postgresql';
import { _decimalDiv } from '../hotel_stay_service/_decimalHelpers';
import { _decimalTruncate } from '../hotel_stay_service/_decimalHelpers';
import { addDays } from 'date-fns';
import { format } from 'date-fns';
import { parseISO } from 'date-fns';
import { subDays } from 'date-fns';
import { bufferEvents } from '../eventOutbox';
import { cardOf } from '../functions';
import { cardsOf } from '../functions';
import { getProducer as getMqProducer } from '../mq/producer';
import { projectResponse } from '../support/responseProjection';
import { transactionUnit } from '../transactionUnit';
import { ApiExtraModels, ApiResponse, ApiBearerAuth } from '@nestjs/swagger';

@ApiExtraModels(AssignRequest, CalendarStay, ConditionRequest, DeskStay, DeskSummary, NoteRequest, OccupancyPoint, RoomCard, StayCard)
@UseGuards(AuthGuard)
@Controller('api/v1/desk')
export class DeskAPIController {
  constructor(
    private readonly functionsService: FunctionsService,
    private readonly roomTypeService: RoomTypeService,
    private readonly stayService: StayService,
    @InjectRepository(Room) private readonly roomRepository: EntityRepository<Room>,
    @InjectRepository(RoomType) private readonly roomTypeRepository: EntityRepository<RoomType>,
    @InjectRepository(Stay) private readonly stayRepository: EntityRepository<Stay>,
    private readonly stayDbEm: EntityManager,
  ) {}

  @Providers('identity')
  @PrincipalTypes('human')
  @Roles('frontDesk')
  @ApiBearerAuth()
  @Get('arrivals')
  @ApiResponse({ status: 200, type: [StayCard] })
  async getArrivals(
  ): Promise<StayCard[]> {
    return await cardsOf(await (this.stayRepository.getEntityManager() as SqlEntityManager).createQueryBuilder(Stay, 'e_stay').select('*').where('e_stay.arrival = ?', [new Date().toISOString().slice(0, 10)]).andWhere({ status: StayStatus.Confirmed }).orderBy({ 'e_stay.guest_name': 'ASC' }).limit(100).getResultList());
  }

  @Providers('identity')
  @PrincipalTypes('human')
  @Roles('frontDesk')
  @ApiBearerAuth()
  @Get('calendar')
  @ApiResponse({ status: 200, type: [CalendarStay] })
  async getCalendar(
  ): Promise<CalendarStay[]> {
    const stays: Stay[] = await (this.stayRepository.getEntityManager() as SqlEntityManager).createQueryBuilder(Stay, 'e_stay').select('*').andWhere({ status: { $in: [StayStatus.Confirmed, StayStatus.CheckedIn] } }).where('e_stay.departure >= ?', [format(subDays(parseISO(new Date().toISOString().slice(0, 10)), 7), 'yyyy-MM-dd')]).orderBy({ 'e_stay.arrival': 'ASC' }).limit(300).getResultList();
    const bars: CalendarStay[] = [];
    for (const stay of stays) {
      bars.push(Object.assign(new CalendarStay(), { id: stay.id, title: `${stay.guestName}, ${stay.roomTypeName}`, startsAt: new Date(`${stay.arrival}T12:00:00Z`), endsAt: new Date(`${stay.departure}T12:00:00Z`) }));
    }
    return bars;
  }

  // A guest gets a room that is clean and empty, and the row of the room is locked while that is checked.
  @Providers('identity')
  @PrincipalTypes('human')
  @Roles('frontDesk')
  @ApiBearerAuth()
  @Post('check-in')
  @HttpCode(HttpStatus.CREATED)
  @ApiResponse({ status: 201, type: StayCard })
  async postCheckIn(
    @RequestBody("object") body: AssignRequest,
  ): Promise<StayCard> {
    const stay = await this.stayRepository.findOne({ id: body.stayId });
    if (!stay) {
      throw new NotFoundException("Not found");
    }
    if ((stay.status !== StayStatus.Confirmed)) {
      throw new BadMoveError({});
    }
    await bufferEvents(async () => {
      await transactionUnit(this.stayDbEm, async (manager: EntityManager) => {
        const room = await (this.roomRepository.getEntityManager() as SqlEntityManager).createQueryBuilder(Room, 'e_room').select('*').where('e_room.number = ?', [body.roomNumber]).andWhere('e_room.room_type_id = ?', [stay.roomTypeId]).setLockMode(LockMode.PESSIMISTIC_WRITE).getSingleResult();
        if (!room) {
          throw new NotFoundException("Not found");
        }
        if ((room.condition !== RoomCondition.Ready)) {
          throw new RoomNotReadyError({});
        }
        if ((await (this.stayRepository.getEntityManager() as SqlEntityManager).createQueryBuilder(Stay, 'e_stay').select('*').where('e_stay.room_number = ?', [room.number]).andWhere({ status: StayStatus.CheckedIn }).getCount() > 0)) {
          throw new RoomOccupiedError({});
        }
        stay.roomNumber = room.number;
        stay.status = StayStatus.CheckedIn;
        await this.stayRepository.getEntityManager().persistAndFlush(stay);
      });
    });
    return await cardOf(stay);
  }

  @Providers('identity')
  @PrincipalTypes('human')
  @Roles('frontDesk')
  @ApiBearerAuth()
  @Get('departures')
  @ApiResponse({ status: 200, type: [StayCard] })
  async getDepartures(
  ): Promise<StayCard[]> {
    return await cardsOf(await (this.stayRepository.getEntityManager() as SqlEntityManager).createQueryBuilder(Stay, 'e_stay').select('*').where('e_stay.departure <= ?', [new Date().toISOString().slice(0, 10)]).andWhere({ status: StayStatus.CheckedIn }).orderBy({ 'e_stay.guest_name': 'ASC' }).limit(100).getResultList());
  }

  @Providers('identity')
  @PrincipalTypes('human')
  @Roles('frontDesk')
  @ApiBearerAuth()
  @Post('note')
  @HttpCode(HttpStatus.CREATED)
  @ApiResponse({ status: 201, type: StayCard })
  async postNote(
    @RequestBody("object") body: NoteRequest,
  ): Promise<StayCard> {
    const stay = await this.stayRepository.findOne({ id: body.stayId });
    if (!stay) {
      throw new NotFoundException("Not found");
    }
    stay.deskNote = body.note;
    await this.stayRepository.getEntityManager().persistAndFlush(stay);
    return await cardOf(stay);
  }

  @Providers('identity')
  @PrincipalTypes('human')
  @Roles('frontDesk')
  @ApiBearerAuth()
  @Get('occupancy')
  @ApiResponse({ status: 200, type: [OccupancyPoint] })
  async getOccupancy(
  ): Promise<OccupancyPoint[]> {
    const types: RoomType[] = await (this.roomTypeRepository.getEntityManager() as SqlEntityManager).createQueryBuilder(RoomType, 'e_room_type').select('*').where('e_room_type.listed = ?', [true]).limit(50).getResultList();
    const points: OccupancyPoint[] = [];
    for (const ahead of [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]) {
      const night: string = format(addDays(parseISO(new Date().toISOString().slice(0, 10)), ahead), 'yyyy-MM-dd');
      let sold: number = 0;
      let left: number = 0;
      for (const type of types) {
        const taken: number = await this.functionsService.takenOn(type.id, night);
        sold = (sold + taken);
        left = ((left + type.inventory) - taken);
      }
      points.push(Object.assign(new OccupancyPoint(), { night: format(parseISO(night), 'MMM dd'), sold: sold, left: left }));
    }
    return points;
  }

  @Providers('identity')
  @PrincipalTypes('human')
  @Roles('frontDesk')
  @ApiBearerAuth()
  @Get('room_types')
  async listRoomTypes(
    @Query('skip', new RejectRepeatedPipe("skip"), new DefaultValuePipe(0), new ParseIntPipe({ exceptionFactory: () => paramFailure("query", "skip", "invalid") }), new IntRangePipe(0, null, "query", "skip")) skip: number,
    @Query('limit', new RejectRepeatedPipe("limit"), new DefaultValuePipe(20), new ParseIntPipe({ exceptionFactory: () => paramFailure("query", "limit", "invalid") }), new IntRangePipe(1, 100, "query", "limit")) limit: number,
    @Query('listed', new RejectRepeatedPipe("listed"), new ParseBoolPipe({ optional: true, exceptionFactory: () => paramFailure("query", "listed", "invalid") })) listed: boolean | null = null,
  ): Promise<Page<RoomType>> {
    return projectResponse(await (async (): Promise<Page<RoomType>> => {
      const page = Object.assign(new PageRequest(), { offset: skip, limit: limit });
      return this.roomTypeService.findAll(page, listed);
    })(), { kind: 'page', of: { kind: 'entity', entity: 'RoomType' } });
  }

  @Providers('identity')
  @PrincipalTypes('human')
  @Roles('frontDesk')
  @ApiBearerAuth()
  @Post('room_types')
  @HttpCode(HttpStatus.CREATED)
  async createRoomType(
    @RequestBody("object") body: CreateRoomTypeDto,
  ): Promise<RoomType> {
    return projectResponse(await (async (): Promise<RoomType> => {
      const entity = this.roomTypeRepository.create(body as never);
      await this.roomTypeRepository.getEntityManager().persistAndFlush(entity);
      // entity.save(): the row was persisted by the statement above
      return entity;
    })(), { kind: 'entity', entity: 'RoomType' });
  }

  @Providers('identity')
  @PrincipalTypes('human')
  @Roles('frontDesk')
  @ApiBearerAuth()
  @Get('rooms')
  @ApiResponse({ status: 200, type: [RoomCard] })
  async getRooms(
  ): Promise<RoomCard[]> {
    const rows: Room[] = await (this.roomRepository.getEntityManager() as SqlEntityManager).createQueryBuilder(Room, 'e_room').select('*').getResultList();
    const cards: RoomCard[] = [];
    for (const room of rows) {
      cards.push(Object.assign(new RoomCard(), { id: room.id, number: room.number, roomTypeName: room.roomTypeName, floor: room.floor, condition: room.condition }));
    }
    return cards;
  }

  @Providers('identity')
  @PrincipalTypes('human')
  @Roles('frontDesk')
  @ApiBearerAuth()
  @Get('stays')
  async listStays(
    @Query('skip', new RejectRepeatedPipe("skip"), new DefaultValuePipe(0), new ParseIntPipe({ exceptionFactory: () => paramFailure("query", "skip", "invalid") }), new IntRangePipe(0, null, "query", "skip")) skip: number,
    @Query('limit', new RejectRepeatedPipe("limit"), new DefaultValuePipe(20), new ParseIntPipe({ exceptionFactory: () => paramFailure("query", "limit", "invalid") }), new IntRangePipe(1, 100, "query", "limit")) limit: number,
    @Query('roomTypeName', new RejectRepeatedPipe("roomTypeName"), new ValueRulePipe((value: unknown): boolean => (typeof value === 'string') && Array.from(value as string).length <= 80, "query", "roomTypeName")) roomTypeName: string | null = null,
    @Query('guestName', new RejectRepeatedPipe("guestName"), new ValueRulePipe((value: unknown): boolean => (typeof value === 'string') && Array.from(value as string).length <= 200, "query", "guestName")) guestName: string | null = null,
    @Query('arrival', new RejectRepeatedPipe("arrival")) arrival: string | null = null,
    @Query('departure', new RejectRepeatedPipe("departure")) departure: string | null = null,
    @Query('status', new RejectRepeatedPipe("status"), new CoerceStringEnumPipe(StayStatus, true, "query", "status")) status: StayStatus | null = null,
  ): Promise<Page<Stay>> {
    return projectResponse(await (async (): Promise<Page<Stay>> => {
      const page = Object.assign(new PageRequest(), { offset: skip, limit: limit });
      return this.stayService.findAll(page, roomTypeName, guestName, arrival, departure, status);
    })(), { kind: 'page', of: { kind: 'entity', entity: 'Stay' } });
  }

  @Providers('identity')
  @PrincipalTypes('human')
  @Roles('frontDesk')
  @ApiBearerAuth()
  @Get('today')
  @ApiResponse({ status: 200, type: DeskSummary })
  async getToday(
  ): Promise<DeskSummary> {
    const day: string = new Date().toISOString().slice(0, 10);
    let sellable: number = 0;
    const types: RoomType[] = await (this.roomTypeRepository.getEntityManager() as SqlEntityManager).createQueryBuilder(RoomType, 'e_room_type').select('*').where('e_room_type.listed = ?', [true]).limit(50).getResultList();
    let taken: number = 0;
    for (const type of types) {
      sellable = (sellable + type.inventory);
      taken = (taken + await this.functionsService.takenOn(type.id, day));
    }
    return Object.assign(new DeskSummary(), { arrivals: await (this.stayRepository.getEntityManager() as SqlEntityManager).createQueryBuilder(Stay, 'e_stay').select('*').where('e_stay.arrival = ?', [day]).andWhere({ status: StayStatus.Confirmed }).getCount(), departures: await (this.stayRepository.getEntityManager() as SqlEntityManager).createQueryBuilder(Stay, 'e_stay').select('*').where('e_stay.departure = ?', [day]).andWhere({ status: StayStatus.CheckedIn }).getCount(), inHouse: await (this.stayRepository.getEntityManager() as SqlEntityManager).createQueryBuilder(Stay, 'e_stay').select('*').andWhere({ status: StayStatus.CheckedIn }).getCount(), roomsToClean: await (this.roomRepository.getEntityManager() as SqlEntityManager).createQueryBuilder(Room, 'e_room').select('*').andWhere({ condition: RoomCondition.Dirty }).getCount(), occupancyPercent: ((sellable === 0) ? 0 : _decimalTruncate(_decimalDiv((taken * 100), sellable))) });
  }

  @Providers('identity')
  @PrincipalTypes('human')
  @Roles('frontDesk')
  @ApiBearerAuth()
  @Get('stays/:id/free-rooms')
  @ApiResponse({ status: 200, type: [RoomCard] })
  async getStaysByIdFreeRooms(
    @Param('id', new ParseUUIDPipe({ exceptionFactory: () => paramFailure("path", "id", "invalid") })) id: string,
  ): Promise<RoomCard[]> {
    const stay = await this.stayRepository.findOne({ id: id });
    if (!stay) {
      throw new NotFoundException("Not found");
    }
    const rooms: Room[] = await (this.roomRepository.getEntityManager() as SqlEntityManager).createQueryBuilder(Room, 'e_room').select('*').where('e_room.room_type_id = ?', [stay.roomTypeId]).andWhere({ condition: RoomCondition.Ready }).orderBy({ 'e_room.number': 'ASC' }).limit(100).getResultList();
    const free: RoomCard[] = [];
    for (const room of rooms) {
      if ((await (this.stayRepository.getEntityManager() as SqlEntityManager).createQueryBuilder(Stay, 'e_stay').select('*').where('e_stay.room_number = ?', [room.number]).andWhere({ status: StayStatus.CheckedIn }).getCount() === 0)) {
        free.push(Object.assign(new RoomCard(), { id: room.id, number: room.number, roomTypeName: room.roomTypeName, floor: room.floor, condition: room.condition }));
      }
    }
    return free;
  }

  @Providers('identity')
  @PrincipalTypes('human')
  @Roles('frontDesk')
  @ApiBearerAuth()
  @Post('rooms/:id/condition')
  @HttpCode(HttpStatus.CREATED)
  @ApiResponse({ status: 201, type: RoomCard })
  async postRoomsByIdCondition(
    @Param('id', new ParseUUIDPipe({ exceptionFactory: () => paramFailure("path", "id", "invalid") })) id: string,
    @RequestBody("object") body: ConditionRequest,
  ): Promise<RoomCard> {
    const room = await this.roomRepository.findOne({ id: id });
    if (!room) {
      throw new NotFoundException("Not found");
    }
    room.condition = body.condition;
    await this.roomRepository.getEntityManager().persistAndFlush(room);
    return Object.assign(new RoomCard(), { id: room.id, number: room.number, roomTypeName: room.roomTypeName, floor: room.floor, condition: room.condition });
  }

  // Leaving makes the room dirty, so it reaches the housekeeping board by itself.
  @Providers('identity')
  @PrincipalTypes('human')
  @Roles('frontDesk')
  @ApiBearerAuth()
  @Post('stays/:id/check-out')
  @HttpCode(HttpStatus.CREATED)
  @ApiResponse({ status: 201, type: StayCard })
  async postStaysByIdCheckOut(
    @Param('id', new ParseUUIDPipe({ exceptionFactory: () => paramFailure("path", "id", "invalid") })) id: string,
  ): Promise<StayCard> {
    const stay = await this.stayRepository.findOne({ id: id });
    if (!stay) {
      throw new NotFoundException("Not found");
    }
    if ((stay.status !== StayStatus.CheckedIn)) {
      throw new BadMoveError({});
    }
    stay.status = StayStatus.CheckedOut;
    await this.stayRepository.getEntityManager().persistAndFlush(stay);
    const number: string | null = stay.roomNumber;
    if ((number != null)) {
      const roomNumber: string = number;
      const room = await (this.roomRepository.getEntityManager() as SqlEntityManager).createQueryBuilder(Room, 'e_room').select('*').where('e_room.number = ?', [roomNumber]).getSingleResult();
      if (!room) {
        throw new NotFoundException("Not found");
      }
      room.condition = RoomCondition.Dirty;
      await this.roomRepository.getEntityManager().persistAndFlush(room);
    }
    await getMqProducer().publishGuestLeft({ code: stay.code, guestName: stay.guestName, guestEmail: String(stay.guestEmail) });
    return await cardOf(stay);
  }

  @Providers('identity')
  @PrincipalTypes('human')
  @Roles('frontDesk')
  @ApiBearerAuth()
  @Post('stays/:id/cancel')
  @HttpCode(HttpStatus.CREATED)
  @ApiResponse({ status: 201, type: StayCard })
  async postStaysByIdCancel(
    @Param('id', new ParseUUIDPipe({ exceptionFactory: () => paramFailure("path", "id", "invalid") })) id: string,
  ): Promise<StayCard> {
    const stay = await this.stayRepository.findOne({ id: id });
    if (!stay) {
      throw new NotFoundException("Not found");
    }
    if (((stay.status !== StayStatus.Held) && (stay.status !== StayStatus.Confirmed))) {
      throw new CannotCancelError({});
    }
    await this.functionsService.cancelStay(stay);
    return await cardOf(stay);
  }

  @Providers('identity')
  @PrincipalTypes('human')
  @Roles('frontDesk')
  @ApiBearerAuth()
  @Delete('room_types/:id')
  @HttpCode(HttpStatus.NO_CONTENT)
  async deleteRoomType(
    @Param('id', new ParseUUIDPipe({ exceptionFactory: () => paramFailure("path", "id", "invalid") })) id: string,
  ): Promise<void> {
    const entity: RoomType | null = await this.roomTypeRepository.findOne({ id: id });
    if (!entity) throw new NotFoundException('entity not found');
    await this.roomTypeRepository.getEntityManager().removeAndFlush(entity);
  }

  @Providers('identity')
  @PrincipalTypes('human')
  @Roles('frontDesk')
  @ApiBearerAuth()
  @Get('room_types/:id')
  async getRoomType(
    @Param('id', new ParseUUIDPipe({ exceptionFactory: () => paramFailure("path", "id", "invalid") })) id: string,
  ): Promise<RoomType> {
    return projectResponse(await (async (): Promise<RoomType> => {
      return this.roomTypeService.findOne(id);
    })(), { kind: 'entity', entity: 'RoomType' });
  }

  @Providers('identity')
  @PrincipalTypes('human')
  @Roles('frontDesk')
  @ApiBearerAuth()
  @Put('room_types/:id')
  async updateRoomType(
    @Param('id', new ParseUUIDPipe({ exceptionFactory: () => paramFailure("path", "id", "invalid") })) id: string,
    @RequestBody("object") body: UpdateRoomTypeDto,
  ): Promise<RoomType> {
    return projectResponse(await (async (): Promise<RoomType> => {
      const entity: RoomType | null = await this.roomTypeRepository.findOne({ id: id });
      if (!entity) throw new NotFoundException('entity not found');
      Object.assign(entity, body);
      await this.roomTypeRepository.getEntityManager().persistAndFlush(entity);
      return entity;
    })(), { kind: 'entity', entity: 'RoomType' });
  }

  @Providers('identity')
  @PrincipalTypes('human')
  @Roles('frontDesk')
  @ApiBearerAuth()
  @Get('stays/:id')
  @ApiResponse({ status: 200, type: DeskStay })
  async getStaysById(
    @Param('id', new ParseUUIDPipe({ exceptionFactory: () => paramFailure("path", "id", "invalid") })) id: string,
  ): Promise<DeskStay> {
    const stay = await this.stayRepository.findOne({ id: id });
    if (!stay) {
      throw new NotFoundException("Not found");
    }
    return Object.assign(new DeskStay(), { stay: await cardOf(stay), guestEmail: String(stay.guestEmail), deskNote: stay.deskNote! });
  }

}
