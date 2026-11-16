import { Injectable, NotFoundException, Logger } from '@nestjs/common';
import { EntityManager } from '@mikro-orm/core';
import { Page, PageWindow, toPage } from '../dto/page';
import { RoomType } from '../hotel_stay_service/entities/stay_db/room-type.entity';
import { CreateRoomTypeDto } from '../dto/create-room-type.dto';
import { UpdateRoomTypeDto } from '../dto/update-room-type.dto';

@Injectable()
export class RoomTypeService {
  private readonly logger = new Logger(RoomTypeService.name);

  constructor(
    private readonly em: EntityManager,
  ) {}

  async findAll(request: PageWindow, listed: boolean | null = null): Promise<Page<RoomType>> {
    this.logger.log('Finding a page of RoomType');
    const where: Record<string, unknown> = {};
    if (listed !== undefined && listed !== null) {
      where['listed'] = listed;
    }
    const [items, total] = await this.em.findAndCount(RoomType, where as never, {
      orderBy: [
        { "id": "asc" },
      ] as never,
      limit: request.limit,
      offset: request.offset,
    });
    return toPage(items, total, request);
  }

  async findOne(id: string): Promise<RoomType> {
    const entity = await this.em.findOne(RoomType, { id } as never);
    if (!entity) {
      throw new NotFoundException(`RoomType with id ${id} not found`);
    }
    return entity;
  }

  async create(dto: CreateRoomTypeDto): Promise<RoomType> {
    const entity = this.em.create(RoomType, dto as never);
    await this.em.persistAndFlush(entity);
    return entity;
  }

  async update(id: string, dto: UpdateRoomTypeDto): Promise<RoomType> {
    const entity = await this.findOne(id);
    this.em.assign(entity, dto as never);
    await this.em.flush();
    return entity;
  }

  async remove(id: string): Promise<void> {
    const entity = await this.findOne(id);
    await this.em.removeAndFlush(entity);
  }

  async getByName(name: string): Promise<RoomType> {
    const entity = await this.em.findOne(RoomType, {
      name    } as never);
    if (!entity) {
      throw new NotFoundException(`RoomType with name ${ name } not found`);
    }
    return entity;
  }

}
