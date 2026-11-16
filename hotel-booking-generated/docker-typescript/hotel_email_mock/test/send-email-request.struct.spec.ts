import { validate } from 'class-validator';
import { instanceToPlain, plainToInstance } from 'class-transformer';
import { SendEmailRequest } from '../src/dto/send-email-request.struct';

describe('SendEmailRequest Struct', () => {
  function buildValidPayload(): Record<string, unknown> {
    return {
      to: 'hello',
      subject: 'foo_bar',
      body: 'world',
      idempotencyKey: 'sample_text',
    };
  }

  it("struct/SendEmailRequest/create_instance", () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(SendEmailRequest, payload);
    expect(instance).toBeDefined();
    expect(instance.to).toBeDefined();
    expect(instance.subject).toBeDefined();
    expect(instance.body).toBeDefined();
    expect(instance.idempotencyKey).toBeDefined();
  });

  it("struct/SendEmailRequest/passes_validation", async () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(SendEmailRequest, payload);
    const errors = await validate(instance);
    expect(errors.length).toBe(0);
  });

  it("struct/SendEmailRequest/to/required", async () => {
    const payload = buildValidPayload();
    delete payload.to;
    const instance = plainToInstance(SendEmailRequest, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/SendEmailRequest/subject/required", async () => {
    const payload = buildValidPayload();
    delete payload.subject;
    const instance = plainToInstance(SendEmailRequest, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/SendEmailRequest/body/required", async () => {
    const payload = buildValidPayload();
    delete payload.body;
    const instance = plainToInstance(SendEmailRequest, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/SendEmailRequest/idempotencyKey/required", async () => {
    const payload = buildValidPayload();
    delete payload.idempotencyKey;
    const instance = plainToInstance(SendEmailRequest, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/SendEmailRequest/serialization_round_trip", () => {
    const instance = plainToInstance(SendEmailRequest, buildValidPayload());
    const restored = plainToInstance(SendEmailRequest, instanceToPlain(instance));
    expect(restored).toEqual(instance);
  });
});
