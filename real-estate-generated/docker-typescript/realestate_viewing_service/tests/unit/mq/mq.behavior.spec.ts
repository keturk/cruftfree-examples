/**
 * Behavior tests for pubsub schemas, producer envelopes, and handler dispatch
 * (auto-generated). Sibling to contracts.spec.ts (ensure-clause tests only).
 */
import { plainToInstance } from 'class-transformer';
import { validate } from 'class-validator';
import {
  ListingPriceChangedPayload,
} from '../../../src/mq/schemas';

describe('ListingPriceChangedPayload', () => {
  it("pubsub_behavior/mq/ListingPriceChanged/schema_field_names", () => {
    const payload: ListingPriceChangedPayload = {
      listingId: '00000000-0000-4000-8000-000000000001',
      title: 'test',
      oldPrice: '99.99',
      newPrice: '99.992',
    };
    expect(Object.keys(payload).sort()).toEqual(["listingId", "newPrice", "oldPrice", "title"]);
  });

  it("pubsub_behavior/mq/ListingPriceChanged/schema_constructs", async () => {
    const instance = plainToInstance(ListingPriceChangedPayload, {
      listingId: '00000000-0000-4000-8000-000000000001',
      title: 'test',
      oldPrice: '99.99',
      newPrice: '99.992',
    });
    expect(await validate(instance)).toHaveLength(0);
    expect(Object.keys(instance).sort()).toEqual(["listingId", "newPrice", "oldPrice", "title"]);
  });

  it("pubsub_behavior/mq/ListingPriceChanged/schema_rejects_missing_required", async () => {
    const instance = plainToInstance(ListingPriceChangedPayload, {});
    expect((await validate(instance)).length).toBeGreaterThan(0);
  });

  it("pubsub_behavior/mq/ListingPriceChanged/schema_json_round_trip", () => {
    const payload: ListingPriceChangedPayload = {
      listingId: '00000000-0000-4000-8000-000000000001',
      title: 'test',
      oldPrice: '99.99',
      newPrice: '99.992',
    };
    const restored = JSON.parse(JSON.stringify(payload)) as Record<string, unknown>;
    expect(Object.keys(restored).sort()).toEqual(["listingId", "newPrice", "oldPrice", "title"]);
  });
});

describe('producer envelope shape', () => {
  it("pubsub_behavior/mq/ListingPriceChanged/envelope_shape", () => {
    const payload: ListingPriceChangedPayload = {
      listingId: '00000000-0000-4000-8000-000000000001',
      title: 'test',
      oldPrice: '99.99',
      newPrice: '99.992',
    };
    const envelope = {
      eventType: 'ListingPriceChanged',
      payload: payload,
    };
    const parsed = JSON.parse(JSON.stringify(envelope)) as {
      eventType: string;
      payload: Record<string, unknown>;
    };
    expect(parsed.eventType).toBe('ListingPriceChanged');
    expect(Object.keys(parsed.payload).sort()).toEqual(["listingId", "newPrice", "oldPrice", "title"]);
  });

});
import { KafkaEventConsumer } from '../../../src/mq/consumer';

// The consumer's dispatch table is an instance field. Its constructor only
// stores its collaborators, so constructing it with none builds the table
// without reaching any engine.
function dispatchTable(): Record<string, ReadonlyArray<unknown>> {
  const consumer = Reflect.construct(KafkaEventConsumer, []) as unknown as {
    handlerMap: Record<string, ReadonlyArray<unknown>>;
  };
  return consumer.handlerMap;
}

describe('handler dispatch table', () => {
  it("pubsub_behavior/mq/dispatch_covers_events", () => {
    const table = dispatchTable();
    for (const key of ["realestate_listing_service.mq.listing_events:ListingPriceChanged"]) {
      expect(Object.keys(table)).toContain(key);
    }
  });

  it("pubsub_behavior/mq/dispatch_entry_shape", () => {
    for (const handlers of Object.values(dispatchTable())) {
      expect(Array.isArray(handlers)).toBe(true);
    }
  });

  it("pubsub_behavior/mq/dispatch_handlers_callable", () => {
    for (const handlers of Object.values(dispatchTable())) {
      expect(handlers.length).toBeGreaterThan(0);
      for (const handler of handlers) {
        expect(typeof handler).toBe('function');
      }
    }
  });
});
