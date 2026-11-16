import { validate } from 'class-validator';
import { instanceToPlain, plainToInstance } from 'class-transformer';
import { Preapproval } from '../src/dto/preapproval.struct';
import { PreapprovalDecision } from '../src/enums/preapproval-decision.enum';

describe('Preapproval Struct', () => {
  function buildValidPayload(): Record<string, unknown> {
    return {
      reference: 'sample_text',
      decision: PreapprovalDecision.Approved,
    };
  }

  it("struct/Preapproval/create_instance", () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(Preapproval, payload);
    expect(instance).toBeDefined();
    expect(instance.reference).toBeDefined();
    expect(instance.decision).toBeDefined();
  });

  it("struct/Preapproval/passes_validation", async () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(Preapproval, payload);
    const errors = await validate(instance);
    expect(errors.length).toBe(0);
  });

  it("struct/Preapproval/reference/required", async () => {
    const payload = buildValidPayload();
    delete payload.reference;
    const instance = plainToInstance(Preapproval, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/Preapproval/decision/required", async () => {
    const payload = buildValidPayload();
    delete payload.decision;
    const instance = plainToInstance(Preapproval, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/Preapproval/serialization_round_trip", () => {
    const instance = plainToInstance(Preapproval, buildValidPayload());
    const restored = plainToInstance(Preapproval, instanceToPlain(instance));
    expect(restored).toEqual(instance);
  });
});
