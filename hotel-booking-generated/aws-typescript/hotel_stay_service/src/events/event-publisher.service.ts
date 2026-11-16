import { Injectable, Logger } from '@nestjs/common';
import { ArrivingTomorrowEvent } from './arriving-tomorrow.event';
import type { ArrivingTomorrowPayload } from '../mq/schemas';
import { GuestLeftEvent } from './guest-left.event';
import type { GuestLeftPayload } from '../mq/schemas';
import { HoldLapsedEvent } from './hold-lapsed.event';
import type { HoldLapsedPayload } from '../mq/schemas';
import { StayCancelledEvent } from './stay-cancelled.event';
import type { StayCancelledPayload } from '../mq/schemas';
import { StayConfirmedEvent } from './stay-confirmed.event';
import type { StayConfirmedPayload } from '../mq/schemas';

@Injectable()
export class StayServiceEventPublisher {
  private readonly logger = new Logger(StayServiceEventPublisher.name);

  constructor(private readonly eventBus: { publish: (event: unknown) => Promise<void> }) {}

  async publishArrivingTomorrow(payload: Partial<ArrivingTomorrowPayload>): Promise<void> {
    this.logger.log(`Publishing ArrivingTomorrow`);
    await this.eventBus.publish(new ArrivingTomorrowEvent(payload as ArrivingTomorrowPayload));
  }
  async publishGuestLeft(payload: Partial<GuestLeftPayload>): Promise<void> {
    this.logger.log(`Publishing GuestLeft`);
    await this.eventBus.publish(new GuestLeftEvent(payload as GuestLeftPayload));
  }
  async publishHoldLapsed(payload: Partial<HoldLapsedPayload>): Promise<void> {
    this.logger.log(`Publishing HoldLapsed`);
    await this.eventBus.publish(new HoldLapsedEvent(payload as HoldLapsedPayload));
  }
  async publishStayCancelled(payload: Partial<StayCancelledPayload>): Promise<void> {
    this.logger.log(`Publishing StayCancelled`);
    await this.eventBus.publish(new StayCancelledEvent(payload as StayCancelledPayload));
  }
  async publishStayConfirmed(payload: Partial<StayConfirmedPayload>): Promise<void> {
    this.logger.log(`Publishing StayConfirmed`);
    await this.eventBus.publish(new StayConfirmedEvent(payload as StayConfirmedPayload));
  }
}
