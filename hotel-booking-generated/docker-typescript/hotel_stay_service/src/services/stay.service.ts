import { Injectable, NotFoundException, Logger } from '@nestjs/common';
import { StayStatus } from '../enums/stay-status.enum'
import { EntityManager } from '@mikro-orm/core';
import { Page, PageWindow, toPage } from '../dto/page';
import { Stay } from '../hotel_stay_service/entities/stay_db/stay.entity';
import { CreateStayDto } from '../dto/create-stay.dto';
import { UpdateStayDto } from '../dto/update-stay.dto';

@Injectable()
export class StayService {
  private readonly logger = new Logger(StayService.name);

  constructor(
    private readonly em: EntityManager,
  ) {}

  async findAll(request: PageWindow, roomTypeName: string | null = null, guestName: string | null = null, arrival: string | null = null, departure: string | null = null, status: StayStatus | null = null): Promise<Page<Stay>> {
    this.logger.log('Finding a page of Stay');
    const where: Record<string, unknown> = {};
    if (roomTypeName !== undefined && roomTypeName !== null) {
      where['roomTypeName'] = roomTypeName;
    }
    if (guestName !== undefined && guestName !== null) {
      where['guestName'] = guestName;
    }
    if (arrival !== undefined && arrival !== null) {
      where['arrival'] = arrival;
    }
    if (departure !== undefined && departure !== null) {
      where['departure'] = departure;
    }
    if (status !== undefined && status !== null) {
      where['status'] = status;
    }
    const [items, total] = await this.em.findAndCount(Stay, where as never, {
      orderBy: [
        { "id": "asc" },
      ] as never,
      limit: request.limit,
      offset: request.offset,
    });
    return toPage(items, total, request);
  }

  async findOne(id: string): Promise<Stay> {
    const entity = await this.em.findOne(Stay, { id } as never);
    if (!entity) {
      throw new NotFoundException(`Stay with id ${id} not found`);
    }
    return entity;
  }

  async create(dto: CreateStayDto): Promise<Stay> {
    const entity = this.em.create(Stay, dto as never);
    await this.em.persistAndFlush(entity);
    return entity;
  }

  async update(id: string, dto: UpdateStayDto): Promise<Stay> {
    const entity = await this.findOne(id);
    this.em.assign(entity, dto as never);
    await this.em.flush();
    return entity;
  }

  async remove(id: string): Promise<void> {
    const entity = await this.findOne(id);
    await this.em.removeAndFlush(entity);
  }

  async getByCode(code: string): Promise<Stay> {
    const entity = await this.em.findOne(Stay, {
      code    } as never);
    if (!entity) {
      throw new NotFoundException(`Stay with code ${ code } not found`);
    }
    return entity;
  }
  async findByRoomTypeId(roomTypeId: string, request: PageWindow): Promise<Page<Stay>> {
    const [items, total] = await this.em.findAndCount(
      Stay,
      { roomTypeId } as never,
      { limit: request.limit, offset: request.offset },
    );
    return toPage(items, total, request);
  }
  async findByGuestId(guestId: string, request: PageWindow): Promise<Page<Stay>> {
    const [items, total] = await this.em.findAndCount(
      Stay,
      { guestId } as never,
      { limit: request.limit, offset: request.offset },
    );
    return toPage(items, total, request);
  }
  async findByRoomTypeIdAndArrivalAndDeparture(roomTypeId: string, arrival: string, departure: string, request: PageWindow): Promise<Page<Stay>> {
    const [items, total] = await this.em.findAndCount(
      Stay,
      { roomTypeId, arrival, departure } as never,
      { limit: request.limit, offset: request.offset },
    );
    return toPage(items, total, request);
  }
  async findByStatusAndHoldUntil(status: StayStatus, holdUntil: Date | null, request: PageWindow): Promise<Page<Stay>> {
    const [items, total] = await this.em.findAndCount(
      Stay,
      { status, holdUntil } as never,
      { limit: request.limit, offset: request.offset },
    );
    return toPage(items, total, request);
  }

}
