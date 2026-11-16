import { Injectable, NotFoundException, Logger } from '@nestjs/common';
import { EntityManager } from '@mikro-orm/core';
import { Page, PageWindow, toPage } from '../dto/page';
import { Notice } from '../hotel_notice_service/entities/notice_db/notice.entity';
import { CreateNoticeDto } from '../dto/create-notice.dto';
import { UpdateNoticeDto } from '../dto/update-notice.dto';

@Injectable()
export class NoticeService {
  private readonly logger = new Logger(NoticeService.name);

  constructor(
    private readonly em: EntityManager,
  ) {}

  async findAll(request: PageWindow, recipient: string | null = null, delivered: boolean | null = null): Promise<Page<Notice>> {
    this.logger.log('Finding a page of Notice');
    const where: Record<string, unknown> = {};
    if (recipient !== undefined && recipient !== null) {
      where['recipient'] = recipient;
    }
    if (delivered !== undefined && delivered !== null) {
      where['delivered'] = delivered;
    }
    const [items, total] = await this.em.findAndCount(Notice, where as never, {
      orderBy: [
        { "id": "asc" },
      ] as never,
      limit: request.limit,
      offset: request.offset,
    });
    return toPage(items, total, request);
  }

  async findOne(id: string): Promise<Notice> {
    const entity = await this.em.findOne(Notice, { id } as never);
    if (!entity) {
      throw new NotFoundException(`Notice with id ${id} not found`);
    }
    return entity;
  }

  async create(dto: CreateNoticeDto): Promise<Notice> {
    const entity = this.em.create(Notice, dto as never);
    await this.em.persistAndFlush(entity);
    return entity;
  }

  async update(id: string, dto: UpdateNoticeDto): Promise<Notice> {
    const entity = await this.findOne(id);
    this.em.assign(entity, dto as never);
    await this.em.flush();
    return entity;
  }

  async remove(id: string): Promise<void> {
    const entity = await this.findOne(id);
    await this.em.removeAndFlush(entity);
  }

  async findByDelivered(delivered: boolean, request: PageWindow): Promise<Page<Notice>> {
    const [items, total] = await this.em.findAndCount(
      Notice,
      { delivered } as never,
      { limit: request.limit, offset: request.offset },
    );
    return toPage(items, total, request);
  }
  async getByNoticeKey(noticeKey: string): Promise<Notice> {
    const entity = await this.em.findOne(Notice, {
      noticeKey    } as never);
    if (!entity) {
      throw new NotFoundException(`Notice with noticeKey ${ noticeKey } not found`);
    }
    return entity;
  }

}
