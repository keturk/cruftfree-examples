import { Injectable, NotFoundException, Logger } from '@nestjs/common';
import { ListingStatus } from '../enums/listing-status.enum'
import { PropertyKind } from '../enums/property-kind.enum'
import { EntityManager } from '@mikro-orm/core';
import { Page, PageWindow, toPage } from '../dto/page';
import { Listing } from '../realestate_listing_service/entities/listing_db/listing.entity';
import { CreateListingDto } from '../dto/create-listing.dto';
import { UpdateListingDto } from '../dto/update-listing.dto';

@Injectable()
export class ListingService {
  private readonly logger = new Logger(ListingService.name);

  constructor(
    private readonly em: EntityManager,
  ) {}

  async findAll(request: PageWindow, title: string | null = null, neighbourhoodName: string | null = null, kind: PropertyKind | null = null, status: ListingStatus | null = null, agentName: string | null = null): Promise<Page<Listing>> {
    this.logger.log('Finding a page of Listing');
    const where: Record<string, unknown> = {};
    if (title !== undefined && title !== null) {
      where['title'] = title;
    }
    if (neighbourhoodName !== undefined && neighbourhoodName !== null) {
      where['neighbourhoodName'] = neighbourhoodName;
    }
    if (kind !== undefined && kind !== null) {
      where['kind'] = kind;
    }
    if (status !== undefined && status !== null) {
      where['status'] = status;
    }
    if (agentName !== undefined && agentName !== null) {
      where['agentName'] = agentName;
    }
    const [items, total] = await this.em.findAndCount(Listing, where as never, {
      orderBy: [
        { "id": "asc" },
      ] as never,
      limit: request.limit,
      offset: request.offset,
    });
    return toPage(items, total, request);
  }

  async findOne(id: string): Promise<Listing> {
    const entity = await this.em.findOne(Listing, { id } as never);
    if (!entity) {
      throw new NotFoundException(`Listing with id ${id} not found`);
    }
    return entity;
  }

  async create(dto: CreateListingDto): Promise<Listing> {
    const entity = this.em.create(Listing, dto as never);
    await this.em.persistAndFlush(entity);
    return entity;
  }

  async update(id: string, dto: UpdateListingDto): Promise<Listing> {
    const entity = await this.findOne(id);
    this.em.assign(entity, dto as never);
    await this.em.flush();
    return entity;
  }

  async remove(id: string): Promise<void> {
    const entity = await this.findOne(id);
    await this.em.removeAndFlush(entity);
  }

  async findByStatus(status: ListingStatus, request: PageWindow): Promise<Page<Listing>> {
    const [items, total] = await this.em.findAndCount(
      Listing,
      { status } as never,
      { limit: request.limit, offset: request.offset },
    );
    return toPage(items, total, request);
  }
  async findByAgentEmail(agentEmail: string, request: PageWindow): Promise<Page<Listing>> {
    const [items, total] = await this.em.findAndCount(
      Listing,
      { agentEmail } as never,
      { limit: request.limit, offset: request.offset },
    );
    return toPage(items, total, request);
  }
  async findByTitleAndSummaryAndNeighbourhoodName(title: string, summary: string, neighbourhoodName: string, request: PageWindow): Promise<Page<Listing>> {
    const [items, total] = await this.em.findAndCount(
      Listing,
      { title, summary, neighbourhoodName } as never,
      { limit: request.limit, offset: request.offset },
    );
    return toPage(items, total, request);
  }

}
