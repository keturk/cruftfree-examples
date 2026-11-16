import { validate } from 'class-validator';
import { instanceToPlain, plainToInstance } from 'class-transformer';
import { StayCard } from '../src/dto/stay-card.struct';
import { StayStatus } from '../src/enums/stay-status.enum';

describe('StayCard Struct', () => {
  function buildValidPayload(): Record<string, unknown> {
    return {
      id: 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
      code: 'sample_text',
      roomTypeName: 'hello',
      roomNumber: 'world',
      guestName: 'hello',
      arrival: '2024-11-05',
      departure: '2025-07-22',
      nights: 100,
      guests: 7,
      total: '149.00',
      status: StayStatus.Held,
      holdEnds: new Date('2025-01-15T12:00:00Z'),
      canCancel: true,
    };
  }

  it("struct/StayCard/create_instance", () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(StayCard, payload);
    expect(instance).toBeDefined();
    expect(instance.id).toBeDefined();
    expect(instance.code).toBeDefined();
    expect(instance.roomTypeName).toBeDefined();
    expect(instance.roomNumber).toBeDefined();
    expect(instance.guestName).toBeDefined();
    expect(instance.arrival).toBeDefined();
    expect(instance.departure).toBeDefined();
    expect(instance.nights).toBeDefined();
    expect(instance.guests).toBeDefined();
    expect(instance.total).toBeDefined();
    expect(instance.status).toBeDefined();
    expect(instance.holdEnds).toBeDefined();
    expect(instance.canCancel).toBeDefined();
  });

  it("struct/StayCard/passes_validation", async () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(StayCard, payload);
    const errors = await validate(instance);
    expect(errors.length).toBe(0);
  });

  it("struct/StayCard/id/required", async () => {
    const payload = buildValidPayload();
    delete payload.id;
    const instance = plainToInstance(StayCard, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/StayCard/code/required", async () => {
    const payload = buildValidPayload();
    delete payload.code;
    const instance = plainToInstance(StayCard, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/StayCard/roomTypeName/required", async () => {
    const payload = buildValidPayload();
    delete payload.roomTypeName;
    const instance = plainToInstance(StayCard, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/StayCard/guestName/required", async () => {
    const payload = buildValidPayload();
    delete payload.guestName;
    const instance = plainToInstance(StayCard, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/StayCard/arrival/required", async () => {
    const payload = buildValidPayload();
    delete payload.arrival;
    const instance = plainToInstance(StayCard, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/StayCard/departure/required", async () => {
    const payload = buildValidPayload();
    delete payload.departure;
    const instance = plainToInstance(StayCard, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/StayCard/nights/required", async () => {
    const payload = buildValidPayload();
    delete payload.nights;
    const instance = plainToInstance(StayCard, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/StayCard/guests/required", async () => {
    const payload = buildValidPayload();
    delete payload.guests;
    const instance = plainToInstance(StayCard, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/StayCard/total/required", async () => {
    const payload = buildValidPayload();
    delete payload.total;
    const instance = plainToInstance(StayCard, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/StayCard/status/required", async () => {
    const payload = buildValidPayload();
    delete payload.status;
    const instance = plainToInstance(StayCard, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/StayCard/holdEnds/required", async () => {
    const payload = buildValidPayload();
    delete payload.holdEnds;
    const instance = plainToInstance(StayCard, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/StayCard/canCancel/required", async () => {
    const payload = buildValidPayload();
    delete payload.canCancel;
    const instance = plainToInstance(StayCard, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/StayCard/serialization_round_trip", () => {
    const instance = plainToInstance(StayCard, buildValidPayload());
    const restored = plainToInstance(StayCard, instanceToPlain(instance));
    expect(restored).toEqual(instance);
  });
});
