import { validate } from 'class-validator';
import { instanceToPlain, plainToInstance } from 'class-transformer';
import { PreapproveRequest } from '../src/dto/preapprove-request.struct';

describe('PreapproveRequest Struct', () => {
  function buildValidPayload(): Record<string, unknown> {
    return {
      applicantName: 'test_string',
      applicantEmail: 'user@example.com',
      amount: '4.50',
      idempotencyKey: 'hello',
    };
  }

  it("struct/PreapproveRequest/create_instance", () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(PreapproveRequest, payload);
    expect(instance).toBeDefined();
    expect(instance.applicantName).toBeDefined();
    expect(instance.applicantEmail).toBeDefined();
    expect(instance.amount).toBeDefined();
    expect(instance.idempotencyKey).toBeDefined();
  });

  it("struct/PreapproveRequest/passes_validation", async () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(PreapproveRequest, payload);
    const errors = await validate(instance);
    expect(errors.length).toBe(0);
  });

  it("struct/PreapproveRequest/applicantName/required", async () => {
    const payload = buildValidPayload();
    delete payload.applicantName;
    const instance = plainToInstance(PreapproveRequest, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/PreapproveRequest/applicantEmail/required", async () => {
    const payload = buildValidPayload();
    delete payload.applicantEmail;
    const instance = plainToInstance(PreapproveRequest, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/PreapproveRequest/amount/required", async () => {
    const payload = buildValidPayload();
    delete payload.amount;
    const instance = plainToInstance(PreapproveRequest, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/PreapproveRequest/idempotencyKey/required", async () => {
    const payload = buildValidPayload();
    delete payload.idempotencyKey;
    const instance = plainToInstance(PreapproveRequest, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/PreapproveRequest/serialization_round_trip", () => {
    const instance = plainToInstance(PreapproveRequest, buildValidPayload());
    const restored = plainToInstance(PreapproveRequest, instanceToPlain(instance));
    expect(restored).toEqual(instance);
  });
});
