import { Injectable, NotFoundException, Logger } from '@nestjs/common';
import { EnvelopeStatus } from '../enums/envelope-status.enum'
import { EntityManager } from '@mikro-orm/core';
import { Page, PageWindow, toPage } from '../dto/page';
import { VendorEnvelope } from '../realestate_signature_mock/entities/signature_db/vendor-envelope.entity';
import { CreateVendorEnvelopeDto } from '../dto/create-vendor-envelope.dto';
import { UpdateVendorEnvelopeDto } from '../dto/update-vendor-envelope.dto';

@Injectable()
export class VendorEnvelopeService {
  private readonly logger = new Logger(VendorEnvelopeService.name);

  constructor(
    private readonly em: EntityManager,
  ) {}

  async findAll(request: PageWindow, signerName: string | null = null, documentTitle: string | null = null, status: EnvelopeStatus | null = null): Promise<Page<VendorEnvelope>> {
    this.logger.log('Finding a page of VendorEnvelope');
    const where: Record<string, unknown> = {};
    if (signerName !== undefined && signerName !== null) {
      where['signerName'] = signerName;
    }
    if (documentTitle !== undefined && documentTitle !== null) {
      where['documentTitle'] = documentTitle;
    }
    if (status !== undefined && status !== null) {
      where['status'] = status;
    }
    const [items, total] = await this.em.findAndCount(VendorEnvelope, where as never, {
      orderBy: [
        { "id": "asc" },
      ] as never,
      limit: request.limit,
      offset: request.offset,
    });
    return toPage(items, total, request);
  }

  async findOne(id: string): Promise<VendorEnvelope> {
    const entity = await this.em.findOne(VendorEnvelope, { id } as never);
    if (!entity) {
      throw new NotFoundException(`VendorEnvelope with id ${id} not found`);
    }
    return entity;
  }

  async create(dto: CreateVendorEnvelopeDto): Promise<VendorEnvelope> {
    const entity = this.em.create(VendorEnvelope, dto as never);
    await this.em.persistAndFlush(entity);
    return entity;
  }

  async update(id: string, dto: UpdateVendorEnvelopeDto): Promise<VendorEnvelope> {
    const entity = await this.findOne(id);
    this.em.assign(entity, dto as never);
    await this.em.flush();
    return entity;
  }

  async remove(id: string): Promise<void> {
    const entity = await this.findOne(id);
    await this.em.removeAndFlush(entity);
  }

  async getByEnvelopeId(envelopeId: string): Promise<VendorEnvelope> {
    const entity = await this.em.findOne(VendorEnvelope, {
      envelopeId    } as never);
    if (!entity) {
      throw new NotFoundException(`VendorEnvelope with envelopeId ${ envelopeId } not found`);
    }
    return entity;
  }
  async getByIdempotencyKey(idempotencyKey: string): Promise<VendorEnvelope> {
    const entity = await this.em.findOne(VendorEnvelope, {
      idempotencyKey    } as never);
    if (!entity) {
      throw new NotFoundException(`VendorEnvelope with idempotencyKey ${ idempotencyKey } not found`);
    }
    return entity;
  }

}
