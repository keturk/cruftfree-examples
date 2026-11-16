import { EventsHandler, IEventHandler } from '@nestjs/cqrs';
import { Logger } from '@nestjs/common';
import { StayCancelledEvent } from './stay-cancelled.event';
import { FunctionsService } from '../functions';

@EventsHandler(StayCancelledEvent)
export class HandleStayCancelledHandler implements IEventHandler<StayCancelledEvent> {
  private readonly logger = new Logger(HandleStayCancelledHandler.name);

  constructor(
    private readonly functionsService: FunctionsService,
  ) {}

  async handle(event: StayCancelledEvent): Promise<void> {
    await this.functionsService.tell(event.payload.guestEmail, `Your stay ${event.payload.code} is cancelled`, `Your ${event.payload.roomTypeName} is cancelled. Anything you paid is on its way back.`, `cancelled-${event.payload.code}`);
  }
}
