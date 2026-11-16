import { Injectable, NotFoundException, Logger } from '@nestjs/common';
import { RoomCondition } from '../enums/room-condition.enum'
import { EntityManager } from '@mikro-orm/core';
import { Page, PageWindow, toPage } from '../dto/page';
import { Room } from '../hotel_stay_service/entities/stay_db/room.entity';
import { CreateRoomDto } from '../dto/create-room.dto';
import { UpdateRoomDto } from '../dto/update-room.dto';

@Injectable()
export class RoomService {
  private readonly logger = new Logger(RoomService.name);

  constructor(
    private readonly em: EntityManager,
  ) {}

  async findAll(request: PageWindow, roomTypeName: string | null = null, condition: RoomCondition | null = null): Promise<Page<Room>> {
    this.logger.log('Finding a page of Room');
    const where: Record<string, unknown> = {};
    if (roomTypeName !== undefined && roomTypeName !== null) {
      where['roomTypeName'] = roomTypeName;
    }
    if (condition !== undefined && condition !== null) {
      where['condition'] = condition;
    }
    const [items, total] = await this.em.findAndCount(Room, where as never, {
      orderBy: [
        { "id": "asc" },
      ] as never,
      limit: request.limit,
      offset: request.offset,
    });
    return toPage(items, total, request);
  }

  async findOne(id: string): Promise<Room> {
    const entity = await this.em.findOne(Room, { id } as never);
    if (!entity) {
      throw new NotFoundException(`Room with id ${id} not found`);
    }
    return entity;
  }

  async create(dto: CreateRoomDto): Promise<Room> {
    const entity = this.em.create(Room, dto as never);
    await this.em.persistAndFlush(entity);
    return entity;
  }

  async update(id: string, dto: UpdateRoomDto): Promise<Room> {
    const entity = await this.findOne(id);
    this.em.assign(entity, dto as never);
    await this.em.flush();
    return entity;
  }

  async remove(id: string): Promise<void> {
    const entity = await this.findOne(id);
    await this.em.removeAndFlush(entity);
  }

  async getByNumber(number: string): Promise<Room> {
    const entity = await this.em.findOne(Room, {
      number    } as never);
    if (!entity) {
      throw new NotFoundException(`Room with number ${ number } not found`);
    }
    return entity;
  }
  async findByRoomTypeId(roomTypeId: string, request: PageWindow): Promise<Page<Room>> {
    const [items, total] = await this.em.findAndCount(
      Room,
      { roomTypeId } as never,
      { limit: request.limit, offset: request.offset },
    );
    return toPage(items, total, request);
  }

}
