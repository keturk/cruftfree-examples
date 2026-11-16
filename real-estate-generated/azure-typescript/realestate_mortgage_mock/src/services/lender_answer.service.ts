import { Injectable, NotFoundException, Logger } from '@nestjs/common';
import { PreapprovalDecision } from '../enums/preapproval-decision.enum'
import { EntityManager } from '@mikro-orm/core';
import { Page, PageWindow, toPage } from '../dto/page';
import { LenderAnswer } from '../realestate_mortgage_mock/entities/mortgage_db/lender-answer.entity';
import { CreateLenderAnswerDto } from '../dto/create-lender-answer.dto';
import { UpdateLenderAnswerDto } from '../dto/update-lender-answer.dto';

@Injectable()
export class LenderAnswerService {
  private readonly logger = new Logger(LenderAnswerService.name);

  constructor(
    private readonly em: EntityManager,
  ) {}

  async findAll(request: PageWindow, applicantName: string | null = null, decision: PreapprovalDecision | null = null): Promise<Page<LenderAnswer>> {
    this.logger.log('Finding a page of LenderAnswer');
    const where: Record<string, unknown> = {};
    if (applicantName !== undefined && applicantName !== null) {
      where['applicantName'] = applicantName;
    }
    if (decision !== undefined && decision !== null) {
      where['decision'] = decision;
    }
    const [items, total] = await this.em.findAndCount(LenderAnswer, where as never, {
      orderBy: [
        { "id": "asc" },
      ] as never,
      limit: request.limit,
      offset: request.offset,
    });
    return toPage(items, total, request);
  }

  async findOne(id: string): Promise<LenderAnswer> {
    const entity = await this.em.findOne(LenderAnswer, { id } as never);
    if (!entity) {
      throw new NotFoundException(`LenderAnswer with id ${id} not found`);
    }
    return entity;
  }

  async create(dto: CreateLenderAnswerDto): Promise<LenderAnswer> {
    const entity = this.em.create(LenderAnswer, dto as never);
    await this.em.persistAndFlush(entity);
    return entity;
  }

  async update(id: string, dto: UpdateLenderAnswerDto): Promise<LenderAnswer> {
    const entity = await this.findOne(id);
    this.em.assign(entity, dto as never);
    await this.em.flush();
    return entity;
  }

  async remove(id: string): Promise<void> {
    const entity = await this.findOne(id);
    await this.em.removeAndFlush(entity);
  }

  async getByReference(reference: string): Promise<LenderAnswer> {
    const entity = await this.em.findOne(LenderAnswer, {
      reference    } as never);
    if (!entity) {
      throw new NotFoundException(`LenderAnswer with reference ${ reference } not found`);
    }
    return entity;
  }
  async getByIdempotencyKey(idempotencyKey: string): Promise<LenderAnswer> {
    const entity = await this.em.findOne(LenderAnswer, {
      idempotencyKey    } as never);
    if (!entity) {
      throw new NotFoundException(`LenderAnswer with idempotencyKey ${ idempotencyKey } not found`);
    }
    return entity;
  }

}
