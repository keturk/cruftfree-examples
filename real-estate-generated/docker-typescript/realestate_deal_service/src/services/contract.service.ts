import { Injectable, NotFoundException, Logger } from '@nestjs/common';
import { ContractStatus } from '../enums/contract-status.enum'
import { EntityManager } from '@mikro-orm/core';
import { Page, PageWindow, toPage } from '../dto/page';
import { Contract } from '../realestate_deal_service/entities/deal_db/contract.entity';
import { CreateContractDto } from '../dto/create-contract.dto';
import { UpdateContractDto } from '../dto/update-contract.dto';

@Injectable()
export class ContractService {
  private readonly logger = new Logger(ContractService.name);

  constructor(
    private readonly em: EntityManager,
  ) {}

  async findAll(request: PageWindow, listingTitle: string | null = null, buyerName: string | null = null, status: ContractStatus | null = null): Promise<Page<Contract>> {
    this.logger.log('Finding a page of Contract');
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
    const [items, total] = await this.em.findAndCount(Contract, where as never, {
      orderBy: [
        { "id": "asc" },
      ] as never,
      limit: request.limit,
      offset: request.offset,
    });
    return toPage(items, total, request);
  }

  async findOne(id: string): Promise<Contract> {
    const entity = await this.em.findOne(Contract, { id } as never);
    if (!entity) {
      throw new NotFoundException(`Contract with id ${id} not found`);
    }
    return entity;
  }

  async create(dto: CreateContractDto): Promise<Contract> {
    const entity = this.em.create(Contract, dto as never);
    await this.em.persistAndFlush(entity);
    return entity;
  }

  async update(id: string, dto: UpdateContractDto): Promise<Contract> {
    const entity = await this.findOne(id);
    this.em.assign(entity, dto as never);
    await this.em.flush();
    return entity;
  }

  async remove(id: string): Promise<void> {
    const entity = await this.findOne(id);
    await this.em.removeAndFlush(entity);
  }

  async getByListingId(listingId: string): Promise<Contract> {
    const entity = await this.em.findOne(Contract, {
      listingId    } as never);
    if (!entity) {
      throw new NotFoundException(`Contract with listingId ${ listingId } not found`);
    }
    return entity;
  }
  async findByBuyerEmail(buyerEmail: string, request: PageWindow): Promise<Page<Contract>> {
    const [items, total] = await this.em.findAndCount(
      Contract,
      { buyerEmail } as never,
      { limit: request.limit, offset: request.offset },
    );
    return toPage(items, total, request);
  }
  async findByAgentEmail(agentEmail: string, request: PageWindow): Promise<Page<Contract>> {
    const [items, total] = await this.em.findAndCount(
      Contract,
      { agentEmail } as never,
      { limit: request.limit, offset: request.offset },
    );
    return toPage(items, total, request);
  }

}
