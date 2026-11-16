import { Injectable, NotFoundException, Logger } from '@nestjs/common';
import { EntityManager } from '@mikro-orm/core';
import { Page, PageWindow, toPage } from '../dto/page';
import { Neighbourhood } from '../realestate_listing_service/entities/listing_db/neighbourhood.entity';
import { CreateNeighbourhoodDto } from '../dto/create-neighbourhood.dto';
import { UpdateNeighbourhoodDto } from '../dto/update-neighbourhood.dto';

@Injectable()
export class NeighbourhoodService {
  private readonly logger = new Logger(NeighbourhoodService.name);

  constructor(
    private readonly em: EntityManager,
  ) {}

  async findAll(request: PageWindow): Promise<Page<Neighbourhood>> {
    this.logger.log('Finding a page of Neighbourhood');
    const where: Record<string, unknown> = {};
    const [items, total] = await this.em.findAndCount(Neighbourhood, where as never, {
      orderBy: [
        { "id": "asc" },
      ] as never,
      limit: request.limit,
      offset: request.offset,
    });
    return toPage(items, total, request);
  }

  async findOne(id: string): Promise<Neighbourhood> {
    const entity = await this.em.findOne(Neighbourhood, { id } as never);
    if (!entity) {
      throw new NotFoundException(`Neighbourhood with id ${id} not found`);
    }
    return entity;
  }

  async create(dto: CreateNeighbourhoodDto): Promise<Neighbourhood> {
    const entity = this.em.create(Neighbourhood, dto as never);
    await this.em.persistAndFlush(entity);
    return entity;
  }

  async update(id: string, dto: UpdateNeighbourhoodDto): Promise<Neighbourhood> {
    const entity = await this.findOne(id);
    this.em.assign(entity, dto as never);
    await this.em.flush();
    return entity;
  }

  async remove(id: string): Promise<void> {
    const entity = await this.findOne(id);
    await this.em.removeAndFlush(entity);
  }

  async getByName(name: string): Promise<Neighbourhood> {
    const entity = await this.em.findOne(Neighbourhood, {
      name    } as never);
    if (!entity) {
      throw new NotFoundException(`Neighbourhood with name ${ name } not found`);
    }
    return entity;
  }

}
