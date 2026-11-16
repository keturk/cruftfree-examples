import { Injectable, NotFoundException, Logger } from '@nestjs/common';
import { Financing } from '../enums/financing.enum'
import { OfferStatus } from '../enums/offer-status.enum'
import { EntityManager } from '@mikro-orm/core';
import { Page, PageWindow, toPage } from '../dto/page';
import { Offer } from '../realestate_deal_service/entities/deal_db/offer.entity';
import { CreateOfferDto } from '../dto/create-offer.dto';
import { UpdateOfferDto } from '../dto/update-offer.dto';

@Injectable()
export class OfferService {
  private readonly logger = new Logger(OfferService.name);

  constructor(
    private readonly em: EntityManager,
  ) {}

  async findAll(request: PageWindow, listingTitle: string | null = null, buyerName: string | null = null, financing: Financing | null = null, status: OfferStatus | null = null): Promise<Page<Offer>> {
    this.logger.log('Finding a page of Offer');
    const where: Record<string, unknown> = {};
    if (listingTitle !== undefined && listingTitle !== null) {
      where['listingTitle'] = listingTitle;
    }
    if (buyerName !== undefined && buyerName !== null) {
      where['buyerName'] = buyerName;
    }
    if (financing !== undefined && financing !== null) {
      where['financing'] = financing;
    }
    if (status !== undefined && status !== null) {
      where['status'] = status;
    }
    const [items, total] = await this.em.findAndCount(Offer, where as never, {
      orderBy: [
        { "id": "asc" },
      ] as never,
      limit: request.limit,
      offset: request.offset,
    });
    return toPage(items, total, request);
  }

  async findOne(id: string): Promise<Offer> {
    const entity = await this.em.findOne(Offer, { id } as never);
    if (!entity) {
      throw new NotFoundException(`Offer with id ${id} not found`);
    }
    return entity;
  }

  async create(dto: CreateOfferDto): Promise<Offer> {
    const entity = this.em.create(Offer, dto as never);
    await this.em.persistAndFlush(entity);
    return entity;
  }

  async update(id: string, dto: UpdateOfferDto): Promise<Offer> {
    const entity = await this.findOne(id);
    this.em.assign(entity, dto as never);
    await this.em.flush();
    return entity;
  }

  async remove(id: string): Promise<void> {
    const entity = await this.findOne(id);
    await this.em.removeAndFlush(entity);
  }

  async findByListingId(listingId: string, request: PageWindow): Promise<Page<Offer>> {
    const [items, total] = await this.em.findAndCount(
      Offer,
      { listingId } as never,
      { limit: request.limit, offset: request.offset },
    );
    return toPage(items, total, request);
  }
  async findByBuyerEmail(buyerEmail: string, request: PageWindow): Promise<Page<Offer>> {
    const [items, total] = await this.em.findAndCount(
      Offer,
      { buyerEmail } as never,
      { limit: request.limit, offset: request.offset },
    );
    return toPage(items, total, request);
  }
  async findByAgentEmail(agentEmail: string, request: PageWindow): Promise<Page<Offer>> {
    const [items, total] = await this.em.findAndCount(
      Offer,
      { agentEmail } as never,
      { limit: request.limit, offset: request.offset },
    );
    return toPage(items, total, request);
  }

}
