import { validate } from 'class-validator';
import { instanceToPlain, plainToInstance } from 'class-transformer';
import { DeskStay } from '../src/dto/desk-stay.struct';
import { StayCard } from '../src/dto/stay-card.struct';
import { StayStatus } from '../src/enums/stay-status.enum';

describe('DeskStay Struct', () => {
  function buildValidPayload(): Record<string, unknown> {
    return {
      stay: {id: 'a1b2c3d4-e5f6-7890-abcd-ef1234567890', code: 'sample_text', roomTypeName: 'hello', roomNumber: 'world', guestName: 'hello', arrival: '2024-11-05', departure: '2025-07-22', nights: 100, guests: 7, total: '149.00', status: StayStatus.Held, holdEnds: new Date('2025-01-15T12:00:00Z'), canCancel: true} as StayCard,
      guestEmail: 'test@demo.io',
      deskNote: 'world',
    };
  }

  it("struct/DeskStay/create_instance", () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(DeskStay, payload);
    expect(instance).toBeDefined();
    expect(instance.stay).toBeDefined();
    expect(instance.guestEmail).toBeDefined();
    expect(instance.deskNote).toBeDefined();
  });

  it("struct/DeskStay/passes_validation", async () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(DeskStay, payload);
    const errors = await validate(instance);
    expect(errors.length).toBe(0);
  });

  it("struct/DeskStay/stay/required", async () => {
    const payload = buildValidPayload();
    delete payload.stay;
    const instance = plainToInstance(DeskStay, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/DeskStay/guestEmail/required", async () => {
    const payload = buildValidPayload();
    delete payload.guestEmail;
    const instance = plainToInstance(DeskStay, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/DeskStay/serialization_round_trip", () => {
    const instance = plainToInstance(DeskStay, buildValidPayload());
    const restored = plainToInstance(DeskStay, instanceToPlain(instance));
    expect(restored).toEqual(instance);
  });
});
