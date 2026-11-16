import type { GuestLeftPayload } from '../mq/schemas';

export class GuestLeftEvent {
  constructor(public readonly payload: GuestLeftPayload) {}
}
