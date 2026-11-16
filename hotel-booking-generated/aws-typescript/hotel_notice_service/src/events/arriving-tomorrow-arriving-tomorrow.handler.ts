import { EventsHandler, IEventHandler } from '@nestjs/cqrs';
import { Logger } from '@nestjs/common';
import { ArrivingTomorrowEvent } from './arriving-tomorrow.event';
import { FunctionsService } from '../functions';

@EventsHandler(ArrivingTomorrowEvent)
export class HandleArrivingTomorrowHandler implements IEventHandler<ArrivingTomorrowEvent> {
  private readonly logger = new Logger(HandleArrivingTomorrowHandler.name);

  constructor(
    private readonly functionsService: FunctionsService,
  ) {}

  async handle(event: ArrivingTomorrowEvent): Promise<void> {
    await this.functionsService.tell(event.payload.guestEmail, `See you tomorrow, ${event.payload.guestName}`, `Your ${event.payload.roomTypeName} will be ready from two o'clock. Your code is ${event.payload.code}.`, `tomorrow-${event.payload.code}`);
  }
}
