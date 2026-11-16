import { validate } from 'class-validator';
import { instanceToPlain, plainToInstance } from 'class-transformer';
import { SendEnvelopeRequest } from '../src/dto/send-envelope-request.struct';

describe('SendEnvelopeRequest Struct', () => {
  function buildValidPayload(): Record<string, unknown> {
    return {
      signerName: 'world',
      signerEmail: 'test@demo.io',
      documentTitle: 'sample_text',
      documentBody: 'The quick brown fox jumps over the lazy dog',
      idempotencyKey: 'foo_bar',
    };
  }

  it("struct/SendEnvelopeRequest/create_instance", () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(SendEnvelopeRequest, payload);
    expect(instance).toBeDefined();
    expect(instance.signerName).toBeDefined();
    expect(instance.signerEmail).toBeDefined();
    expect(instance.documentTitle).toBeDefined();
    expect(instance.documentBody).toBeDefined();
    expect(instance.idempotencyKey).toBeDefined();
  });

  it("struct/SendEnvelopeRequest/passes_validation", async () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(SendEnvelopeRequest, payload);
    const errors = await validate(instance);
    expect(errors.length).toBe(0);
  });

  it("struct/SendEnvelopeRequest/signerName/required", async () => {
    const payload = buildValidPayload();
    delete payload.signerName;
    const instance = plainToInstance(SendEnvelopeRequest, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/SendEnvelopeRequest/signerEmail/required", async () => {
    const payload = buildValidPayload();
    delete payload.signerEmail;
    const instance = plainToInstance(SendEnvelopeRequest, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/SendEnvelopeRequest/documentTitle/required", async () => {
    const payload = buildValidPayload();
    delete payload.documentTitle;
    const instance = plainToInstance(SendEnvelopeRequest, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/SendEnvelopeRequest/documentBody/required", async () => {
    const payload = buildValidPayload();
    delete payload.documentBody;
    const instance = plainToInstance(SendEnvelopeRequest, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/SendEnvelopeRequest/idempotencyKey/required", async () => {
    const payload = buildValidPayload();
    delete payload.idempotencyKey;
    const instance = plainToInstance(SendEnvelopeRequest, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/SendEnvelopeRequest/serialization_round_trip", () => {
    const instance = plainToInstance(SendEnvelopeRequest, buildValidPayload());
    const restored = plainToInstance(SendEnvelopeRequest, instanceToPlain(instance));
    expect(restored).toEqual(instance);
  });
});
