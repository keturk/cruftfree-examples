import { Injectable, NotFoundException, Logger } from '@nestjs/common';
import { DeliveryStatus } from '../enums/delivery-status.enum'
import { EntityManager } from '@mikro-orm/core';
import { Page, PageWindow, toPage } from '../dto/page';
import { Outbound } from '../hotel_email_mock/entities/email_db/outbound.entity';
import { CreateOutboundDto } from '../dto/create-outbound.dto';
import { UpdateOutboundDto } from '../dto/update-outbound.dto';

@Injectable()
export class OutboundService {
  private readonly logger = new Logger(OutboundService.name);

  constructor(
    private readonly em: EntityManager,
  ) {}

  async findAll(request: PageWindow, recipient: string | null = null, subject: string | null = null, status: DeliveryStatus | null = null): Promise<Page<Outbound>> {
    this.logger.log('Finding a page of Outbound');
    const where: Record<string, unknown> = {};
    if (recipient !== undefined && recipient !== null) {
      where['recipient'] = recipient;
    }
    if (subject !== undefined && subject !== null) {
      where['subject'] = subject;
    }
    if (status !== undefined && status !== null) {
      where['status'] = status;
    }
    const [items, total] = await this.em.findAndCount(Outbound, where as never, {
      orderBy: [
        { "id": "asc" },
      ] as never,
      limit: request.limit,
      offset: request.offset,
    });
    return toPage(items, total, request);
  }

  async findOne(id: string): Promise<Outbound> {
    const entity = await this.em.findOne(Outbound, { id } as never);
    if (!entity) {
      throw new NotFoundException(`Outbound with id ${id} not found`);
    }
    return entity;
  }

  async create(dto: CreateOutboundDto): Promise<Outbound> {
    const entity = this.em.create(Outbound, dto as never);
    await this.em.persistAndFlush(entity);
    return entity;
  }

  async update(id: string, dto: UpdateOutboundDto): Promise<Outbound> {
    const entity = await this.findOne(id);
    this.em.assign(entity, dto as never);
    await this.em.flush();
    return entity;
  }

  async remove(id: string): Promise<void> {
    const entity = await this.findOne(id);
    await this.em.removeAndFlush(entity);
  }

  async getByDeliveryId(deliveryId: string): Promise<Outbound> {
    const entity = await this.em.findOne(Outbound, {
      deliveryId    } as never);
    if (!entity) {
      throw new NotFoundException(`Outbound with deliveryId ${ deliveryId } not found`);
    }
    return entity;
  }
  async getByIdempotencyKey(idempotencyKey: string): Promise<Outbound> {
    const entity = await this.em.findOne(Outbound, {
      idempotencyKey    } as never);
    if (!entity) {
      throw new NotFoundException(`Outbound with idempotencyKey ${ idempotencyKey } not found`);
    }
    return entity;
  }

}
