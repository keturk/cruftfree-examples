import { Injectable, Logger } from '@nestjs/common';
import { ListingPriceChangedEvent } from './listing-price-changed.event';
import type { ListingPriceChangedPayload } from '../mq/schemas';

@Injectable()
export class ListingServiceEventPublisher {
  private readonly logger = new Logger(ListingServiceEventPublisher.name);

  constructor(private readonly eventBus: { publish: (event: unknown) => Promise<void> }) {}

  async publishListingPriceChanged(payload: Partial<ListingPriceChangedPayload>): Promise<void> {
    this.logger.log(`Publishing ListingPriceChanged`);
    await this.eventBus.publish(new ListingPriceChangedEvent(payload as ListingPriceChangedPayload));
  }
}
