import { validate } from 'class-validator';
import { instanceToPlain, plainToInstance } from 'class-transformer';
import { PageRequest } from '../src/dto/page-request.struct';

describe('PageRequest Struct', () => {
  function buildValidPayload(): Record<string, unknown> {
    return {
      offset: 256,
      limit: 1,
    };
  }

  it("struct/PageRequest/create_instance", () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(PageRequest, payload);
    expect(instance).toBeDefined();
    expect(instance.offset).toBeDefined();
    expect(instance.limit).toBeDefined();
  });

  it("struct/PageRequest/passes_validation", async () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(PageRequest, payload);
    const errors = await validate(instance);
    expect(errors.length).toBe(0);
  });

  it("struct/PageRequest/offset/required", async () => {
    const payload = buildValidPayload();
    delete payload.offset;
    const instance = plainToInstance(PageRequest, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/PageRequest/limit/required", async () => {
    const payload = buildValidPayload();
    delete payload.limit;
    const instance = plainToInstance(PageRequest, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/PageRequest/serialization_round_trip", () => {
    const instance = plainToInstance(PageRequest, buildValidPayload());
    const restored = plainToInstance(PageRequest, instanceToPlain(instance));
    expect(restored).toEqual(instance);
  });
});
