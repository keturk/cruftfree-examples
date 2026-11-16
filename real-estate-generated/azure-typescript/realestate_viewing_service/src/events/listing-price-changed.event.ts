import type { ListingPriceChangedPayload } from '../mq/schemas';

export class ListingPriceChangedEvent {
  constructor(public readonly payload: ListingPriceChangedPayload) {}
}
