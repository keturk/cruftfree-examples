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
import { Charge } from '../dto/charge.struct';
import { ChargeStatus } from '../enums/charge-status.enum';
import { CreateChargeRequest } from '../dto/create-charge-request.struct';
import { RefundChargeRequest } from '../dto/refund-charge-request.struct';
import { CardCharge } from '../hotel_payment_mock/entities/payment_db/card-charge.entity';
import { DECLINED_TOKEN } from '../constants';
import { NoSuchChargeError } from '../errors/domain-errors';
import { SqlEntityManager } from '@mikro-orm/postgresql';
import { answerOf } from '../functions';
import { randomInt } from 'crypto';
import { ApiExtraModels, ApiResponse, ApiSecurity } from '@nestjs/swagger';

@ApiExtraModels(Charge, CreateChargeRequest, RefundChargeRequest)
@UseGuards(AuthGuard)
@Controller('v1')
export class PaymentAPIController {
  constructor(
    @InjectRepository(CardCharge) private readonly cardChargeRepository: EntityRepository<CardCharge>,
  ) {}

  @Providers('paymentKeys', 'test_auth')
  @PrincipalTypes('human')
  @ApiSecurity("paymentKeys")
  @Post('charges')
  @HttpCode(HttpStatus.CREATED)
  @ApiResponse({ status: 201, type: Charge })
  async postCharges(
    @RequestBody("object") body: CreateChargeRequest,
  ): Promise<Charge> {
    const existing: CardCharge | null = (await (this.cardChargeRepository.getEntityManager() as SqlEntityManager).createQueryBuilder(CardCharge, 'e_card_charge').select('*').where('e_card_charge.idempotency_key = ?', [body.idempotencyKey]).limit(1).getResultList())[0] ?? null;
    if ((existing != null)) {
      return await answerOf(existing);
    }
    const declined: boolean = (body.cardToken === DECLINED_TOKEN);
    const created = this.cardChargeRepository.create({ chargeId: `ch_${Array.from({ length: 24 }, () => '0123456789abcdef'.charAt(randomInt('0123456789abcdef'.length))).join('')}`, idempotencyKey: body.idempotencyKey, amount: body.amount, currency: body.currency, reference: body.reference, status: (declined ? ChargeStatus.Declined : ChargeStatus.Succeeded), declineReason: (declined ? 'The issuer declined this card' : null) } as never);
    await this.cardChargeRepository.getEntityManager().persistAndFlush(created);
    return await answerOf(created);
  }

  @Providers('paymentKeys', 'test_auth')
  @PrincipalTypes('human')
  @ApiSecurity("paymentKeys")
  @Post('refunds')
  @HttpCode(HttpStatus.CREATED)
  @ApiResponse({ status: 201, type: Charge })
  async postRefunds(
    @RequestBody("object") body: RefundChargeRequest,
  ): Promise<Charge> {
    const charge: CardCharge | null = (await (this.cardChargeRepository.getEntityManager() as SqlEntityManager).createQueryBuilder(CardCharge, 'e_card_charge').select('*').where('e_card_charge.charge_id = ?', [body.chargeId]).limit(1).getResultList())[0] ?? null;
    if ((charge == null)) {
      throw new NoSuchChargeError({});
    }
    charge.status = ChargeStatus.Refunded;
    await this.cardChargeRepository.getEntityManager().persistAndFlush(charge);
    return await answerOf(charge);
  }

}
