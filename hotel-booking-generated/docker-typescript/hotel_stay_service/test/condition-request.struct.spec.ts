import { validate } from 'class-validator';
import { instanceToPlain, plainToInstance } from 'class-transformer';
import { ConditionRequest } from '../src/dto/condition-request.struct';
import { RoomCondition } from '../src/enums/room-condition.enum';

describe('ConditionRequest Struct', () => {
  function buildValidPayload(): Record<string, unknown> {
    return {
      condition: RoomCondition.Ready,
    };
  }

  it("struct/ConditionRequest/create_instance", () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(ConditionRequest, payload);
    expect(instance).toBeDefined();
    expect(instance.condition).toBeDefined();
  });

  it("struct/ConditionRequest/passes_validation", async () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(ConditionRequest, payload);
    const errors = await validate(instance);
    expect(errors.length).toBe(0);
  });

  it("struct/ConditionRequest/condition/required", async () => {
    const payload = buildValidPayload();
    delete payload.condition;
    const instance = plainToInstance(ConditionRequest, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/ConditionRequest/serialization_round_trip", () => {
    const instance = plainToInstance(ConditionRequest, buildValidPayload());
    const restored = plainToInstance(ConditionRequest, instanceToPlain(instance));
    expect(restored).toEqual(instance);
  });
});
