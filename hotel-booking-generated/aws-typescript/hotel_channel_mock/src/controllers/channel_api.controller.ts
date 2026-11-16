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
import { AvailabilityPush } from '../dto/availability-push.struct';
import { PushReceipt } from '../dto/push-receipt.struct';
import { PublishedNight } from '../hotel_channel_mock/entities/channel_db/published-night.entity';
import { KNOWN_PROPERTY } from '../constants';
import { SqlEntityManager } from '@mikro-orm/postgresql';
import { UnknownPropertyError } from '../errors/domain-errors';
import { ApiExtraModels, ApiResponse, ApiSecurity } from '@nestjs/swagger';

@ApiExtraModels(AvailabilityPush, PushReceipt)
@UseGuards(AuthGuard)
@Controller('v1')
export class ChannelAPIController {
  constructor(
    @InjectRepository(PublishedNight) private readonly publishedNightRepository: EntityRepository<PublishedNight>,
  ) {}

  @Providers('channelKeys')
  @PrincipalTypes('human')
  @ApiSecurity("channelKeys")
  @Post('availability')
  @HttpCode(HttpStatus.CREATED)
  @ApiResponse({ status: 201, type: PushReceipt })
  async postAvailability(
    @RequestBody("object") body: AvailabilityPush,
  ): Promise<PushReceipt> {
    if ((body.propertyCode !== KNOWN_PROPERTY)) {
      throw new UnknownPropertyError({});
    }
    for (const update of body.nights) {
      const existing: PublishedNight | null = (await (this.publishedNightRepository.getEntityManager() as SqlEntityManager).createQueryBuilder(PublishedNight, 'e_published_night').select('*').where('e_published_night.room_type = ?', [update.roomType]).andWhere('e_published_night.night = ?', [update.night]).limit(1).getResultList())[0] ?? null;
      if ((existing != null)) {
        existing.left = update.left;
        existing.nightlyRate = update.nightlyRate;
        existing.receivedAt = new Date();
        await this.publishedNightRepository.getEntityManager().persistAndFlush(existing);
      } else {
        const entity = this.publishedNightRepository.create({ roomType: update.roomType, night: update.night, left: update.left, nightlyRate: update.nightlyRate, receivedAt: new Date() } as never);
        await this.publishedNightRepository.getEntityManager().persistAndFlush(entity);
      }
    }
    return Object.assign(new PushReceipt(), { accepted: body.nights.length });
  }

}
