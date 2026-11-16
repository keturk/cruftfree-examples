import type { StayCancelledPayload } from '../mq/schemas';

export class StayCancelledEvent {
  constructor(public readonly payload: StayCancelledPayload) {}
}
