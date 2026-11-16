import { Injectable, NotFoundException, Logger } from '@nestjs/common';
import { ViewingStatus } from '../enums/viewing-status.enum'
import { EntityManager } from '@mikro-orm/core';
import { Page, PageWindow, toPage } from '../dto/page';
import { Viewing } from '../realestate_viewing_service/entities/viewing_db/viewing.entity';
import { CreateViewingDto } from '../dto/create-viewing.dto';
import { UpdateViewingDto } from '../dto/update-viewing.dto';

@Injectable()
export class ViewingService {
  private readonly logger = new Logger(ViewingService.name);

  constructor(
    private readonly em: EntityManager,
  ) {}

  async findAll(request: PageWindow, listingTitle: string | null = null, buyerName: string | null = null, status: ViewingStatus | null = null, agentName: string | null = null): Promise<Page<Viewing>> {
    this.logger.log('Finding a page of Viewing');
    const where: Record<string, unknown> = {};
    if (listingTitle !== undefined && listingTitle !== null) {
      where['listingTitle'] = listingTitle;
    }
    if (buyerName !== undefined && buyerName !== null) {
      where['buyerName'] = buyerName;
    }
    if (status !== undefined && status !== null) {
      where['status'] = status;
    }
    if (agentName !== undefined && agentName !== null) {
      where['agentName'] = agentName;
    }
    const [items, total] = await this.em.findAndCount(Viewing, where as never, {
      orderBy: [
        { "id": "asc" },
      ] as never,
      limit: request.limit,
      offset: request.offset,
    });
    return toPage(items, total, request);
  }

  async findOne(id: string): Promise<Viewing> {
    const entity = await this.em.findOne(Viewing, { id } as never);
    if (!entity) {
      throw new NotFoundException(`Viewing with id ${id} not found`);
    }
    return entity;
  }

  async create(dto: CreateViewingDto): Promise<Viewing> {
    const entity = this.em.create(Viewing, dto as never);
    await this.em.persistAndFlush(entity);
    return entity;
  }

  async update(id: string, dto: UpdateViewingDto): Promise<Viewing> {
    const entity = await this.findOne(id);
    this.em.assign(entity, dto as never);
    await this.em.flush();
    return entity;
  }

  async remove(id: string): Promise<void> {
    const entity = await this.findOne(id);
    await this.em.removeAndFlush(entity);
  }

  async findByListingId(listingId: string, request: PageWindow): Promise<Page<Viewing>> {
    const [items, total] = await this.em.findAndCount(
      Viewing,
      { listingId } as never,
      { limit: request.limit, offset: request.offset },
    );
    return toPage(items, total, request);
  }
  async findByBuyerEmail(buyerEmail: string, request: PageWindow): Promise<Page<Viewing>> {
    const [items, total] = await this.em.findAndCount(
      Viewing,
      { buyerEmail } as never,
      { limit: request.limit, offset: request.offset },
    );
    return toPage(items, total, request);
  }
  async findByAgentEmail(agentEmail: string, request: PageWindow): Promise<Page<Viewing>> {
    const [items, total] = await this.em.findAndCount(
      Viewing,
      { agentEmail } as never,
      { limit: request.limit, offset: request.offset },
    );
    return toPage(items, total, request);
  }

}
