import { validate } from 'class-validator';
import { instanceToPlain, plainToInstance } from 'class-transformer';
import { PayRequest } from '../src/dto/pay-request.struct';
import { TestCard } from '../src/enums/test-card.enum';

describe('PayRequest Struct', () => {
  function buildValidPayload(): Record<string, unknown> {
    return {
      stayId: 'f47ac10b-58cc-4372-a567-0e02b2c3d479',
      card: TestCard.CardThatPays,
    };
  }

  it("struct/PayRequest/create_instance", () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(PayRequest, payload);
    expect(instance).toBeDefined();
    expect(instance.stayId).toBeDefined();
    expect(instance.card).toBeDefined();
  });

  it("struct/PayRequest/passes_validation", async () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(PayRequest, payload);
    const errors = await validate(instance);
    expect(errors.length).toBe(0);
  });

  it("struct/PayRequest/stayId/required", async () => {
    const payload = buildValidPayload();
    delete payload.stayId;
    const instance = plainToInstance(PayRequest, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/PayRequest/card/required", async () => {
    const payload = buildValidPayload();
    delete payload.card;
    const instance = plainToInstance(PayRequest, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/PayRequest/serialization_round_trip", () => {
    const instance = plainToInstance(PayRequest, buildValidPayload());
    const restored = plainToInstance(PayRequest, instanceToPlain(instance));
    expect(restored).toEqual(instance);
  });
});
