import type { HoldLapsedPayload } from '../mq/schemas';

export class HoldLapsedEvent {
  constructor(public readonly payload: HoldLapsedPayload) {}
}
