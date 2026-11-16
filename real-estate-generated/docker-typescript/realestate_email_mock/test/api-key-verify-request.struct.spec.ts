import { validate } from 'class-validator';
import { instanceToPlain, plainToInstance } from 'class-transformer';
import { ApiKeyVerifyRequest } from '../src/dto/api-key-verify-request.struct';

describe('ApiKeyVerifyRequest Struct', () => {
  function buildValidPayload(): Record<string, unknown> {
    return {
      keyHash: 'world',
    };
  }

  it("struct/_ApiKeyVerifyRequest/create_instance", () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(ApiKeyVerifyRequest, payload);
    expect(instance).toBeDefined();
    expect(instance.keyHash).toBeDefined();
  });

  it("struct/_ApiKeyVerifyRequest/passes_validation", async () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(ApiKeyVerifyRequest, payload);
    const errors = await validate(instance);
    expect(errors.length).toBe(0);
  });

  it("struct/_ApiKeyVerifyRequest/keyHash/required", async () => {
    const payload = buildValidPayload();
    delete payload.keyHash;
    const instance = plainToInstance(ApiKeyVerifyRequest, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/_ApiKeyVerifyRequest/serialization_round_trip", () => {
    const instance = plainToInstance(ApiKeyVerifyRequest, buildValidPayload());
    const restored = plainToInstance(ApiKeyVerifyRequest, instanceToPlain(instance));
    expect(restored).toEqual(instance);
  });
});
