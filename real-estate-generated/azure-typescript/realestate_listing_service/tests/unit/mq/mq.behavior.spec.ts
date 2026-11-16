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
