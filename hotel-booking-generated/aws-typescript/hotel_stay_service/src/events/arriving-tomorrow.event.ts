import type { ArrivingTomorrowPayload } from '../mq/schemas';

export class ArrivingTomorrowEvent {
  constructor(public readonly payload: ArrivingTomorrowPayload) {}
}
