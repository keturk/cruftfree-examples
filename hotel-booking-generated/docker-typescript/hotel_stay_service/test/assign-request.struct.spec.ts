import { validate } from 'class-validator';
import { instanceToPlain, plainToInstance } from 'class-transformer';
import { AssignRequest } from '../src/dto/assign-request.struct';

describe('AssignRequest Struct', () => {
  function buildValidPayload(): Record<string, unknown> {
    return {
      stayId: 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
      roomNumber: 'sample_t',
    };
  }

  it("struct/AssignRequest/create_instance", () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(AssignRequest, payload);
    expect(instance).toBeDefined();
    expect(instance.stayId).toBeDefined();
    expect(instance.roomNumber).toBeDefined();
  });

  it("struct/AssignRequest/passes_validation", async () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(AssignRequest, payload);
    const errors = await validate(instance);
    expect(errors.length).toBe(0);
  });

  it("struct/AssignRequest/stayId/required", async () => {
    const payload = buildValidPayload();
    delete payload.stayId;
    const instance = plainToInstance(AssignRequest, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/AssignRequest/roomNumber/required", async () => {
    const payload = buildValidPayload();
    delete payload.roomNumber;
    const instance = plainToInstance(AssignRequest, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/AssignRequest/serialization_round_trip", () => {
    const instance = plainToInstance(AssignRequest, buildValidPayload());
    const restored = plainToInstance(AssignRequest, instanceToPlain(instance));
    expect(restored).toEqual(instance);
  });
});
