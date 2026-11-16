import { EventsHandler, IEventHandler } from '@nestjs/cqrs';
import { Logger } from '@nestjs/common';
import { StayConfirmedEvent } from './stay-confirmed.event';
import { FunctionsService } from '../functions';

@EventsHandler(StayConfirmedEvent)
export class HandleStayConfirmedHandler implements IEventHandler<StayConfirmedEvent> {
  private readonly logger = new Logger(HandleStayConfirmedHandler.name);

  constructor(
    private readonly functionsService: FunctionsService,
  ) {}

  async handle(event: StayConfirmedEvent): Promise<void> {
    await this.functionsService.tell(event.payload.guestEmail, `Your stay ${event.payload.code} is booked`, `Hello ${event.payload.guestName}. ${event.payload.roomTypeName}, from ${event.payload.arrival} to ${event.payload.departure}. We have taken ${event.payload.total}. Keep this code for the desk: ${event.payload.code}.`, `booked-${event.payload.code}`);
  }
}
