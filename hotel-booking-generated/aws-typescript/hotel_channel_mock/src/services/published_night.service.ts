import { Injectable, NotFoundException, Logger } from '@nestjs/common';
import { EntityManager } from '@mikro-orm/core';
import { Page, PageWindow, toPage } from '../dto/page';
import { PublishedNight } from '../hotel_channel_mock/entities/channel_db/published-night.entity';
import { CreatePublishedNightDto } from '../dto/create-published-night.dto';
import { UpdatePublishedNightDto } from '../dto/update-published-night.dto';

@Injectable()
export class PublishedNightService {
  private readonly logger = new Logger(PublishedNightService.name);

  constructor(
    private readonly em: EntityManager,
  ) {}

  async findAll(request: PageWindow, roomType: string | null = null, night: string | null = null): Promise<Page<PublishedNight>> {
    this.logger.log('Finding a page of PublishedNight');
    const where: Record<string, unknown> = {};
    if (roomType !== undefined && roomType !== null) {
      where['roomType'] = roomType;
    }
    if (night !== undefined && night !== null) {
      where['night'] = night;
    }
    const [items, total] = await this.em.findAndCount(PublishedNight, where as never, {
      orderBy: [
        { "id": "asc" },
      ] as never,
      limit: request.limit,
      offset: request.offset,
    });
    return toPage(items, total, request);
  }

  async findOne(id: string): Promise<PublishedNight> {
    const entity = await this.em.findOne(PublishedNight, { id } as never);
    if (!entity) {
      throw new NotFoundException(`PublishedNight with id ${id} not found`);
    }
    return entity;
  }

  async create(dto: CreatePublishedNightDto): Promise<PublishedNight> {
    const entity = this.em.create(PublishedNight, dto as never);
    await this.em.persistAndFlush(entity);
    return entity;
  }

  async update(id: string, dto: UpdatePublishedNightDto): Promise<PublishedNight> {
    const entity = await this.findOne(id);
    this.em.assign(entity, dto as never);
    await this.em.flush();
    return entity;
  }

  async remove(id: string): Promise<void> {
    const entity = await this.findOne(id);
    await this.em.removeAndFlush(entity);
  }

  async getByRoomTypeAndNight(roomType: string, night: string): Promise<PublishedNight> {
    const entity = await this.em.findOne(PublishedNight, {
roomType, night    } as never);
    if (!entity) {
      throw new NotFoundException(`PublishedNight not found`);
    }
    return entity;
  }

}
