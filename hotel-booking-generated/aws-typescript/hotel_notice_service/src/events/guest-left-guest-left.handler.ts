import { EventsHandler, IEventHandler } from '@nestjs/cqrs';
import { Logger } from '@nestjs/common';
import { GuestLeftEvent } from './guest-left.event';
import { FunctionsService } from '../functions';

@EventsHandler(GuestLeftEvent)
export class HandleGuestLeftHandler implements IEventHandler<GuestLeftEvent> {
  private readonly logger = new Logger(HandleGuestLeftHandler.name);

  constructor(
    private readonly functionsService: FunctionsService,
  ) {}

  async handle(event: GuestLeftEvent): Promise<void> {
    await this.functionsService.tell(event.payload.guestEmail, `Thank you for staying, ${event.payload.guestName}`, `We hope to see you again. Your stay was ${event.payload.code}.`, `thanks-${event.payload.code}`);
  }
}
