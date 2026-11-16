import { EventsHandler, IEventHandler } from '@nestjs/cqrs';
import { Logger } from '@nestjs/common';
import { HoldLapsedEvent } from './hold-lapsed.event';
import { FunctionsService } from '../functions';

@EventsHandler(HoldLapsedEvent)
export class HandleHoldLapsedHandler implements IEventHandler<HoldLapsedEvent> {
  private readonly logger = new Logger(HandleHoldLapsedHandler.name);

  constructor(
    private readonly functionsService: FunctionsService,
  ) {}

  async handle(event: HoldLapsedEvent): Promise<void> {
    await this.functionsService.tell(event.payload.guestEmail, `We let go of your ${event.payload.roomTypeName}`, `Your hold ran out before payment, so the room is back on sale. You have not been charged.`, `lapsed-${event.payload.code}`);
  }
}
