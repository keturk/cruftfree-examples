import { validate } from 'class-validator';
import { instanceToPlain, plainToInstance } from 'class-transformer';
import { DealSummary } from '../src/dto/deal-summary.struct';

describe('DealSummary Struct', () => {
  function buildValidPayload(): Record<string, unknown> {
    return {
      offersWaiting: 100,
      contractsOut: 256,
      signed: 100,
      signedValue: '19.99',
    };
  }

  it("struct/DealSummary/create_instance", () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(DealSummary, payload);
    expect(instance).toBeDefined();
    expect(instance.offersWaiting).toBeDefined();
    expect(instance.contractsOut).toBeDefined();
    expect(instance.signed).toBeDefined();
    expect(instance.signedValue).toBeDefined();
  });

  it("struct/DealSummary/passes_validation", async () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(DealSummary, payload);
    const errors = await validate(instance);
    expect(errors.length).toBe(0);
  });

  it("struct/DealSummary/offersWaiting/required", async () => {
    const payload = buildValidPayload();
    delete payload.offersWaiting;
    const instance = plainToInstance(DealSummary, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/DealSummary/contractsOut/required", async () => {
    const payload = buildValidPayload();
    delete payload.contractsOut;
    const instance = plainToInstance(DealSummary, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/DealSummary/signed/required", async () => {
    const payload = buildValidPayload();
    delete payload.signed;
    const instance = plainToInstance(DealSummary, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/DealSummary/signedValue/required", async () => {
    const payload = buildValidPayload();
    delete payload.signedValue;
    const instance = plainToInstance(DealSummary, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/DealSummary/serialization_round_trip", () => {
    const instance = plainToInstance(DealSummary, buildValidPayload());
    const restored = plainToInstance(DealSummary, instanceToPlain(instance));
    expect(restored).toEqual(instance);
  });
});
