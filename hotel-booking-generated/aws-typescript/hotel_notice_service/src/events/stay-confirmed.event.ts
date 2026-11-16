import type { StayConfirmedPayload } from '../mq/schemas';

export class StayConfirmedEvent {
  constructor(public readonly payload: StayConfirmedPayload) {}
}
