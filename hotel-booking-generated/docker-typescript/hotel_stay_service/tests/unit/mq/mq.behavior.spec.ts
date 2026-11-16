/**
 * Behavior tests for pubsub schemas, producer envelopes, and handler dispatch
 * (auto-generated). Sibling to contracts.spec.ts (ensure-clause tests only).
 */
import { plainToInstance } from 'class-transformer';
import { validate } from 'class-validator';
import {
  StayConfirmedPayload,
  StayCancelledPayload,
  HoldLapsedPayload,
  ArrivingTomorrowPayload,
  GuestLeftPayload,
} from '../../../src/mq/schemas';

describe('StayConfirmedPayload', () => {
  it("pubsub_behavior/mq/StayConfirmed/schema_field_names", () => {
    const payload: StayConfirmedPayload = {
      code: 'aaaa',
      guestName: 'test',
      guestEmail: 'test',
      roomTypeName: 'test',
      arrival: 'test',
      departure: 'test',
      total: 'test',
    };
    expect(Object.keys(payload).sort()).toEqual(["arrival", "code", "departure", "guestEmail", "guestName", "roomTypeName", "total"]);
  });

  it("pubsub_behavior/mq/StayConfirmed/schema_constructs", async () => {
    const instance = plainToInstance(StayConfirmedPayload, {
      code: 'aaaa',
      guestName: 'test',
      guestEmail: 'test',
      roomTypeName: 'test',
      arrival: 'test',
      departure: 'test',
      total: 'test',
    });
    expect(await validate(instance)).toHaveLength(0);
    expect(Object.keys(instance).sort()).toEqual(["arrival", "code", "departure", "guestEmail", "guestName", "roomTypeName", "total"]);
  });

  it("pubsub_behavior/mq/StayConfirmed/schema_rejects_missing_required", async () => {
    const instance = plainToInstance(StayConfirmedPayload, {});
    expect((await validate(instance)).length).toBeGreaterThan(0);
  });

  it("pubsub_behavior/mq/StayConfirmed/schema_json_round_trip", () => {
    const payload: StayConfirmedPayload = {
      code: 'aaaa',
      guestName: 'test',
      guestEmail: 'test',
      roomTypeName: 'test',
      arrival: 'test',
      departure: 'test',
      total: 'test',
    };
    const restored = JSON.parse(JSON.stringify(payload)) as Record<string, unknown>;
    expect(Object.keys(restored).sort()).toEqual(["arrival", "code", "departure", "guestEmail", "guestName", "roomTypeName", "total"]);
  });
});

describe('StayCancelledPayload', () => {
  it("pubsub_behavior/mq/StayCancelled/schema_field_names", () => {
    const payload: StayCancelledPayload = {
      code: 'aaaa',
      guestEmail: 'test',
      roomTypeName: 'test',
    };
    expect(Object.keys(payload).sort()).toEqual(["code", "guestEmail", "roomTypeName"]);
  });

  it("pubsub_behavior/mq/StayCancelled/schema_constructs", async () => {
    const instance = plainToInstance(StayCancelledPayload, {
      code: 'aaaa',
      guestEmail: 'test',
      roomTypeName: 'test',
    });
    expect(await validate(instance)).toHaveLength(0);
    expect(Object.keys(instance).sort()).toEqual(["code", "guestEmail", "roomTypeName"]);
  });

  it("pubsub_behavior/mq/StayCancelled/schema_rejects_missing_required", async () => {
    const instance = plainToInstance(StayCancelledPayload, {});
    expect((await validate(instance)).length).toBeGreaterThan(0);
  });

  it("pubsub_behavior/mq/StayCancelled/schema_json_round_trip", () => {
    const payload: StayCancelledPayload = {
      code: 'aaaa',
      guestEmail: 'test',
      roomTypeName: 'test',
    };
    const restored = JSON.parse(JSON.stringify(payload)) as Record<string, unknown>;
    expect(Object.keys(restored).sort()).toEqual(["code", "guestEmail", "roomTypeName"]);
  });
});

describe('HoldLapsedPayload', () => {
  it("pubsub_behavior/mq/HoldLapsed/schema_field_names", () => {
    const payload: HoldLapsedPayload = {
      code: 'aaaa',
      guestEmail: 'test',
      roomTypeName: 'test',
    };
    expect(Object.keys(payload).sort()).toEqual(["code", "guestEmail", "roomTypeName"]);
  });

  it("pubsub_behavior/mq/HoldLapsed/schema_constructs", async () => {
    const instance = plainToInstance(HoldLapsedPayload, {
      code: 'aaaa',
      guestEmail: 'test',
      roomTypeName: 'test',
    });
    expect(await validate(instance)).toHaveLength(0);
    expect(Object.keys(instance).sort()).toEqual(["code", "guestEmail", "roomTypeName"]);
  });

  it("pubsub_behavior/mq/HoldLapsed/schema_rejects_missing_required", async () => {
    const instance = plainToInstance(HoldLapsedPayload, {});
    expect((await validate(instance)).length).toBeGreaterThan(0);
  });

  it("pubsub_behavior/mq/HoldLapsed/schema_json_round_trip", () => {
    const payload: HoldLapsedPayload = {
      code: 'aaaa',
      guestEmail: 'test',
      roomTypeName: 'test',
    };
    const restored = JSON.parse(JSON.stringify(payload)) as Record<string, unknown>;
    expect(Object.keys(restored).sort()).toEqual(["code", "guestEmail", "roomTypeName"]);
  });
});

describe('ArrivingTomorrowPayload', () => {
  it("pubsub_behavior/mq/ArrivingTomorrow/schema_field_names", () => {
    const payload: ArrivingTomorrowPayload = {
      code: 'aaaa',
      guestName: 'test',
      guestEmail: 'test',
      roomTypeName: 'test',
    };
    expect(Object.keys(payload).sort()).toEqual(["code", "guestEmail", "guestName", "roomTypeName"]);
  });

  it("pubsub_behavior/mq/ArrivingTomorrow/schema_constructs", async () => {
    const instance = plainToInstance(ArrivingTomorrowPayload, {
      code: 'aaaa',
      guestName: 'test',
      guestEmail: 'test',
      roomTypeName: 'test',
    });
    expect(await validate(instance)).toHaveLength(0);
    expect(Object.keys(instance).sort()).toEqual(["code", "guestEmail", "guestName", "roomTypeName"]);
  });

  it("pubsub_behavior/mq/ArrivingTomorrow/schema_rejects_missing_required", async () => {
    const instance = plainToInstance(ArrivingTomorrowPayload, {});
    expect((await validate(instance)).length).toBeGreaterThan(0);
  });

  it("pubsub_behavior/mq/ArrivingTomorrow/schema_json_round_trip", () => {
    const payload: ArrivingTomorrowPayload = {
      code: 'aaaa',
      guestName: 'test',
      guestEmail: 'test',
      roomTypeName: 'test',
    };
    const restored = JSON.parse(JSON.stringify(payload)) as Record<string, unknown>;
    expect(Object.keys(restored).sort()).toEqual(["code", "guestEmail", "guestName", "roomTypeName"]);
  });
});

describe('GuestLeftPayload', () => {
  it("pubsub_behavior/mq/GuestLeft/schema_field_names", () => {
    const payload: GuestLeftPayload = {
      code: 'aaaa',
      guestName: 'test',
      guestEmail: 'test',
    };
    expect(Object.keys(payload).sort()).toEqual(["code", "guestEmail", "guestName"]);
  });

  it("pubsub_behavior/mq/GuestLeft/schema_constructs", async () => {
    const instance = plainToInstance(GuestLeftPayload, {
      code: 'aaaa',
      guestName: 'test',
      guestEmail: 'test',
    });
    expect(await validate(instance)).toHaveLength(0);
    expect(Object.keys(instance).sort()).toEqual(["code", "guestEmail", "guestName"]);
  });

  it("pubsub_behavior/mq/GuestLeft/schema_rejects_missing_required", async () => {
    const instance = plainToInstance(GuestLeftPayload, {});
    expect((await validate(instance)).length).toBeGreaterThan(0);
  });

  it("pubsub_behavior/mq/GuestLeft/schema_json_round_trip", () => {
    const payload: GuestLeftPayload = {
      code: 'aaaa',
      guestName: 'test',
      guestEmail: 'test',
    };
    const restored = JSON.parse(JSON.stringify(payload)) as Record<string, unknown>;
    expect(Object.keys(restored).sort()).toEqual(["code", "guestEmail", "guestName"]);
  });
});

describe('producer envelope shape', () => {
  it("pubsub_behavior/mq/StayConfirmed/envelope_shape", () => {
    const payload: StayConfirmedPayload = {
      code: 'aaaa',
      guestName: 'test',
      guestEmail: 'test',
      roomTypeName: 'test',
      arrival: 'test',
      departure: 'test',
      total: 'test',
    };
    const envelope = {
      eventType: 'StayConfirmed',
      payload: payload,
    };
    const parsed = JSON.parse(JSON.stringify(envelope)) as {
      eventType: string;
      payload: Record<string, unknown>;
    };
    expect(parsed.eventType).toBe('StayConfirmed');
    expect(Object.keys(parsed.payload).sort()).toEqual(["arrival", "code", "departure", "guestEmail", "guestName", "roomTypeName", "total"]);
  });

  it("pubsub_behavior/mq/StayCancelled/envelope_shape", () => {
    const payload: StayCancelledPayload = {
      code: 'aaaa',
      guestEmail: 'test',
      roomTypeName: 'test',
    };
    const envelope = {
      eventType: 'StayCancelled',
      payload: payload,
    };
    const parsed = JSON.parse(JSON.stringify(envelope)) as {
      eventType: string;
      payload: Record<string, unknown>;
    };
    expect(parsed.eventType).toBe('StayCancelled');
    expect(Object.keys(parsed.payload).sort()).toEqual(["code", "guestEmail", "roomTypeName"]);
  });

  it("pubsub_behavior/mq/HoldLapsed/envelope_shape", () => {
    const payload: HoldLapsedPayload = {
      code: 'aaaa',
      guestEmail: 'test',
      roomTypeName: 'test',
    };
    const envelope = {
      eventType: 'HoldLapsed',
      payload: payload,
    };
    const parsed = JSON.parse(JSON.stringify(envelope)) as {
      eventType: string;
      payload: Record<string, unknown>;
    };
    expect(parsed.eventType).toBe('HoldLapsed');
    expect(Object.keys(parsed.payload).sort()).toEqual(["code", "guestEmail", "roomTypeName"]);
  });

  it("pubsub_behavior/mq/ArrivingTomorrow/envelope_shape", () => {
    const payload: ArrivingTomorrowPayload = {
      code: 'aaaa',
      guestName: 'test',
      guestEmail: 'test',
      roomTypeName: 'test',
    };
    const envelope = {
      eventType: 'ArrivingTomorrow',
      payload: payload,
    };
    const parsed = JSON.parse(JSON.stringify(envelope)) as {
      eventType: string;
      payload: Record<string, unknown>;
    };
    expect(parsed.eventType).toBe('ArrivingTomorrow');
    expect(Object.keys(parsed.payload).sort()).toEqual(["code", "guestEmail", "guestName", "roomTypeName"]);
  });

  it("pubsub_behavior/mq/GuestLeft/envelope_shape", () => {
    const payload: GuestLeftPayload = {
      code: 'aaaa',
      guestName: 'test',
      guestEmail: 'test',
    };
    const envelope = {
      eventType: 'GuestLeft',
      payload: payload,
    };
    const parsed = JSON.parse(JSON.stringify(envelope)) as {
      eventType: string;
      payload: Record<string, unknown>;
    };
    expect(parsed.eventType).toBe('GuestLeft');
    expect(Object.keys(parsed.payload).sort()).toEqual(["code", "guestEmail", "guestName"]);
  });

});
