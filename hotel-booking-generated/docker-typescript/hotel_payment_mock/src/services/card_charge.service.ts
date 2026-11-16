import { Injectable, NotFoundException, Logger } from '@nestjs/common';
import { ChargeStatus } from '../enums/charge-status.enum'
import { EntityManager } from '@mikro-orm/core';
import { Page, PageWindow, toPage } from '../dto/page';
import { CardCharge } from '../hotel_payment_mock/entities/payment_db/card-charge.entity';
import { CreateCardChargeDto } from '../dto/create-card-charge.dto';
import { UpdateCardChargeDto } from '../dto/update-card-charge.dto';

@Injectable()
export class CardChargeService {
  private readonly logger = new Logger(CardChargeService.name);

  constructor(
    private readonly em: EntityManager,
  ) {}

  async findAll(request: PageWindow, reference: string | null = null, status: ChargeStatus | null = null): Promise<Page<CardCharge>> {
    this.logger.log('Finding a page of CardCharge');
    const where: Record<string, unknown> = {};
    if (reference !== undefined && reference !== null) {
      where['reference'] = reference;
    }
    if (status !== undefined && status !== null) {
      where['status'] = status;
    }
    const [items, total] = await this.em.findAndCount(CardCharge, where as never, {
      orderBy: [
        { "id": "asc" },
      ] as never,
      limit: request.limit,
      offset: request.offset,
    });
    return toPage(items, total, request);
  }

  async findOne(id: string): Promise<CardCharge> {
    const entity = await this.em.findOne(CardCharge, { id } as never);
    if (!entity) {
      throw new NotFoundException(`CardCharge with id ${id} not found`);
    }
    return entity;
  }

  async create(dto: CreateCardChargeDto): Promise<CardCharge> {
    const entity = this.em.create(CardCharge, dto as never);
    await this.em.persistAndFlush(entity);
    return entity;
  }

  async update(id: string, dto: UpdateCardChargeDto): Promise<CardCharge> {
    const entity = await this.findOne(id);
    this.em.assign(entity, dto as never);
    await this.em.flush();
    return entity;
  }

  async remove(id: string): Promise<void> {
    const entity = await this.findOne(id);
    await this.em.removeAndFlush(entity);
  }

  async getByChargeId(chargeId: string): Promise<CardCharge> {
    const entity = await this.em.findOne(CardCharge, {
      chargeId    } as never);
    if (!entity) {
      throw new NotFoundException(`CardCharge with chargeId ${ chargeId } not found`);
    }
    return entity;
  }
  async getByIdempotencyKey(idempotencyKey: string): Promise<CardCharge> {
    const entity = await this.em.findOne(CardCharge, {
      idempotencyKey    } as never);
    if (!entity) {
      throw new NotFoundException(`CardCharge with idempotencyKey ${ idempotencyKey } not found`);
    }
    return entity;
  }

}
