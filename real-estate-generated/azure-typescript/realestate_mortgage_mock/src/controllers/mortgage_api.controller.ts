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
import { Preapproval } from '../dto/preapproval.struct';
import { PreapprovalDecision } from '../enums/preapproval-decision.enum';
import { PreapproveRequest } from '../dto/preapprove-request.struct';
import { LenderAnswer } from '../realestate_mortgage_mock/entities/mortgage_db/lender-answer.entity';
import { APPROVAL_LIMIT } from '../constants';
import { SqlEntityManager } from '@mikro-orm/postgresql';
import { _decimalToNumber } from '../realestate_mortgage_mock/_decimalHelpers';
import { randomInt } from 'crypto';
import { ApiExtraModels, ApiResponse, ApiSecurity } from '@nestjs/swagger';

@ApiExtraModels(Preapproval, PreapproveRequest)
@UseGuards(AuthGuard)
@Controller('v1')
export class MortgageAPIController {
  constructor(
    @InjectRepository(LenderAnswer) private readonly lenderAnswerRepository: EntityRepository<LenderAnswer>,
  ) {}

  @Providers('mortgageKeys')
  @PrincipalTypes('human')
  @ApiSecurity("mortgageKeys")
  @Post('preapprovals')
  @HttpCode(HttpStatus.CREATED)
  @ApiResponse({ status: 201, type: Preapproval })
  async postPreapprovals(
    @RequestBody("object") body: PreapproveRequest,
  ): Promise<Preapproval> {
    const existing: LenderAnswer | null = (await (this.lenderAnswerRepository.getEntityManager() as SqlEntityManager).createQueryBuilder(LenderAnswer, 'e_lender_answer').select('*').where('e_lender_answer.idempotency_key = ?', [body.idempotencyKey]).limit(1).getResultList())[0] ?? null;
    if ((existing != null)) {
      return Object.assign(new Preapproval(), { reference: existing.reference, decision: existing.decision });
    }
    const created = this.lenderAnswerRepository.create({ applicantName: body.applicantName, applicantEmail: body.applicantEmail, amount: body.amount, decision: ((_decimalToNumber(body.amount) > APPROVAL_LIMIT) ? PreapprovalDecision.Declined : PreapprovalDecision.Approved), reference: `pre_${Array.from({ length: 24 }, () => '0123456789abcdef'.charAt(randomInt('0123456789abcdef'.length))).join('')}`, idempotencyKey: body.idempotencyKey } as never);
    await this.lenderAnswerRepository.getEntityManager().persistAndFlush(created);
    return Object.assign(new Preapproval(), { reference: created.reference, decision: created.decision });
  }

}
