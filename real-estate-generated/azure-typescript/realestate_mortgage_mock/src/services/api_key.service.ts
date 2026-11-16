import { Injectable, NotFoundException, Logger } from '@nestjs/common';
import { EntityManager } from '@mikro-orm/core';
import { Page, PageWindow, toPage } from '../dto/page';
import { ApiKey } from '../realestate_mortgage_mock/entities/mortgage_db/api-key.entity';
import { CreateApiKeyDto } from '../dto/create-api-key.dto';
import { UpdateApiKeyDto } from '../dto/update-api-key.dto';

@Injectable()
export class ApiKeyService {
  private readonly logger = new Logger(ApiKeyService.name);

  constructor(
    private readonly em: EntityManager,
  ) {}

  async findAll(request: PageWindow): Promise<Page<ApiKey>> {
    this.logger.log('Finding a page of ApiKey');
    const where: Record<string, unknown> = {};
    const [items, total] = await this.em.findAndCount(ApiKey, where as never, {
      orderBy: [
        { "id": "asc" },
      ] as never,
      limit: request.limit,
      offset: request.offset,
    });
    return toPage(items, total, request);
  }

  async findOne(id: string): Promise<ApiKey> {
    const entity = await this.em.findOne(ApiKey, { id } as never);
    if (!entity) {
      throw new NotFoundException(`ApiKey with id ${id} not found`);
    }
    return entity;
  }

  async create(dto: CreateApiKeyDto): Promise<ApiKey> {
    const entity = this.em.create(ApiKey, dto as never);
    await this.em.persistAndFlush(entity);
    return entity;
  }

  async update(id: string, dto: UpdateApiKeyDto): Promise<ApiKey> {
    const entity = await this.findOne(id);
    this.em.assign(entity, dto as never);
    await this.em.flush();
    return entity;
  }

  async remove(id: string): Promise<void> {
    const entity = await this.findOne(id);
    await this.em.removeAndFlush(entity);
  }

  async getByKeyHash(keyHash: string): Promise<ApiKey> {
    const entity = await this.em.findOne(ApiKey, {
      keyHash    } as never);
    if (!entity) {
      throw new NotFoundException(`ApiKey with keyHash ${ keyHash } not found`);
    }
    return entity;
  }
  async findByOwnerId(ownerId: string, request: PageWindow): Promise<Page<ApiKey>> {
    const [items, total] = await this.em.findAndCount(
      ApiKey,
      { ownerId } as never,
      { limit: request.limit, offset: request.offset },
    );
    return toPage(items, total, request);
  }

}
