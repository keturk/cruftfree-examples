import { Injectable, NotFoundException, Logger } from '@nestjs/common';
import { EntityManager } from '@mikro-orm/core';
import { Page, PageWindow, toPage } from '../dto/page';
import { PriceChange } from '../realestate_listing_service/entities/listing_db/price-change.entity';
import { CreatePriceChangeDto } from '../dto/create-price-change.dto';

@Injectable()
export class PriceChangeService {
  private readonly logger = new Logger(PriceChangeService.name);

  constructor(
    private readonly em: EntityManager,
  ) {}

  async findAll(request: PageWindow): Promise<Page<PriceChange>> {
    this.logger.log('Finding a page of PriceChange');
    const where: Record<string, unknown> = {};
    const [items, total] = await this.em.findAndCount(PriceChange, where as never, {
      orderBy: [
        { "id": "asc" },
      ] as never,
      limit: request.limit,
      offset: request.offset,
    });
    return toPage(items, total, request);
  }

  async findOne(id: string): Promise<PriceChange> {
    const entity = await this.em.findOne(PriceChange, { id } as never);
    if (!entity) {
      throw new NotFoundException(`PriceChange with id ${id} not found`);
    }
    return entity;
  }

  async create(dto: CreatePriceChangeDto): Promise<PriceChange> {
    const entity = this.em.create(PriceChange, dto as never);
    await this.em.persistAndFlush(entity);
    return entity;
  }


  async findByListingId(listingId: string, request: PageWindow): Promise<Page<PriceChange>> {
    const [items, total] = await this.em.findAndCount(
      PriceChange,
      { listingId } as never,
      { limit: request.limit, offset: request.offset },
    );
    return toPage(items, total, request);
  }

}
