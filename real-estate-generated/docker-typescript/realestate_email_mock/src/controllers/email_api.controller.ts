import {
  Controller,
  Post,
  Param,
  HttpCode,
  HttpStatus,
  UseGuards,
} from '@nestjs/common';
import { AuthGuard } from '../auth/auth.guard';
import { PrincipalTypes } from '../auth/optional-auth.decorator';
import { Providers } from '../auth/providers.decorator';
import { RequestBody, paramFailure } from '../common/request-validation';
import { InjectRepository } from '@mikro-orm/nestjs';
import { EntityRepository } from '@mikro-orm/core';
import { Delivery } from '../dto/delivery.struct';
import { DeliveryStatus } from '../enums/delivery-status.enum';
import { SendEmailRequest } from '../dto/send-email-request.struct';
import { Outbound } from '../realestate_email_mock/entities/email_db/outbound.entity';
import { BOUNCING_DOMAIN } from '../constants';
import { SqlEntityManager } from '@mikro-orm/postgresql';
import { randomInt } from 'crypto';
import { ApiExtraModels, ApiResponse, ApiSecurity } from '@nestjs/swagger';

@ApiExtraModels(Delivery, SendEmailRequest)
@UseGuards(AuthGuard)
@Controller('v1')
export class EmailAPIController {
  constructor(
    @InjectRepository(Outbound) private readonly outboundRepository: EntityRepository<Outbound>,
  ) {}

  @Providers('emailKeys', 'test_auth')
  @PrincipalTypes('human')
  @ApiSecurity("emailKeys")
  @Post('deliveries')
  @HttpCode(HttpStatus.CREATED)
  @ApiResponse({ status: 201, type: Delivery })
  async postDeliveries(
    @RequestBody("object") body: SendEmailRequest,
  ): Promise<Delivery> {
    const existing: Outbound | null = (await (this.outboundRepository.getEntityManager() as SqlEntityManager).createQueryBuilder(Outbound, 'e_outbound').select('*').where('e_outbound.idempotency_key = ?', [body.idempotencyKey]).limit(1).getResultList())[0] ?? null;
    if ((existing != null)) {
      return Object.assign(new Delivery(), { id: existing.deliveryId, status: existing.status });
    }
    const created = this.outboundRepository.create({ deliveryId: `mail_${Array.from({ length: 24 }, () => '0123456789abcdef'.charAt(randomInt('0123456789abcdef'.length))).join('')}`, idempotencyKey: body.idempotencyKey, recipient: body.to, subject: body.subject, body: body.body, status: (body.to.endsWith(BOUNCING_DOMAIN) ? DeliveryStatus.Bounced : DeliveryStatus.Delivered) } as never);
    await this.outboundRepository.getEntityManager().persistAndFlush(created);
    return Object.assign(new Delivery(), { id: created.deliveryId, status: created.status });
  }

}
