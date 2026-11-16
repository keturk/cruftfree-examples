import { EventsHandler, IEventHandler } from '@nestjs/cqrs';
import { Logger } from '@nestjs/common';
import { ListingPriceChangedEvent } from './listing-price-changed.event';
import { EntityRepository } from '@mikro-orm/core';
import { InjectRepository } from '@mikro-orm/nestjs';
import { SqlEntityManager } from '@mikro-orm/postgresql';
import { Viewing } from '../realestate_viewing_service/entities/viewing_db/viewing.entity';
import { ViewingStatus } from '../enums/viewing-status.enum';
import { _decimalText } from '../realestate_viewing_service/_decimalHelpers';
import { sendMail } from '../functions';

@EventsHandler(ListingPriceChangedEvent)
export class HandleListingPriceChangedHandler implements IEventHandler<ListingPriceChangedEvent> {
  private readonly logger = new Logger(HandleListingPriceChangedHandler.name);

  constructor(
    @InjectRepository(Viewing) private readonly viewingRepository: EntityRepository<Viewing>,
  ) {}

  async handle(event: ListingPriceChangedEvent): Promise<void> {
    const upcoming: Viewing[] = await (this.viewingRepository.getEntityManager() as SqlEntityManager).createQueryBuilder(Viewing, 'e_viewing').select('*').where('e_viewing.listing_id = ?', [event.payload.listingId]).andWhere({ status: { $in: [ViewingStatus.Requested, ViewingStatus.Confirmed] } }).where('e_viewing.starts_at >= ?', [new Date()]).limit(100).getResultList();
    for (const viewing of upcoming) {
      await sendMail(String(viewing.buyerEmail), `New price for ${event.payload.title}`, `The home you are going to see now asks $${_decimalText(event.payload.newPrice)}.`, `price-${viewing.id}-${_decimalText(event.payload.newPrice)}`);
    }
  }
}
