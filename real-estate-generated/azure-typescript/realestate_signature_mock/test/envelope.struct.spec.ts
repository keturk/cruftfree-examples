import { validate } from 'class-validator';
import { instanceToPlain, plainToInstance } from 'class-transformer';
import { Envelope } from '../src/dto/envelope.struct';
import { EnvelopeStatus } from '../src/enums/envelope-status.enum';

describe('Envelope Struct', () => {
  function buildValidPayload(): Record<string, unknown> {
    return {
      id: 'test_string',
      status: EnvelopeStatus.Sent,
    };
  }

  it("struct/Envelope/create_instance", () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(Envelope, payload);
    expect(instance).toBeDefined();
    expect(instance.id).toBeDefined();
    expect(instance.status).toBeDefined();
  });

  it("struct/Envelope/passes_validation", async () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(Envelope, payload);
    const errors = await validate(instance);
    expect(errors.length).toBe(0);
  });

  it("struct/Envelope/id/required", async () => {
    const payload = buildValidPayload();
    delete payload.id;
    const instance = plainToInstance(Envelope, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/Envelope/status/required", async () => {
    const payload = buildValidPayload();
    delete payload.status;
    const instance = plainToInstance(Envelope, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/Envelope/serialization_round_trip", () => {
    const instance = plainToInstance(Envelope, buildValidPayload());
    const restored = plainToInstance(Envelope, instanceToPlain(instance));
    expect(restored).toEqual(instance);
  });
});
