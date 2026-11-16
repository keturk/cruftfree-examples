import { validate } from 'class-validator';
import { instanceToPlain, plainToInstance } from 'class-transformer';
import { AgentSummary } from '../src/dto/agent-summary.struct';

describe('AgentSummary Struct', () => {
  function buildValidPayload(): Record<string, unknown> {
    return {
      onTheMarket: 1,
      drafts: 1,
      underOffer: 1,
      sold: 42,
    };
  }

  it("struct/AgentSummary/create_instance", () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(AgentSummary, payload);
    expect(instance).toBeDefined();
    expect(instance.onTheMarket).toBeDefined();
    expect(instance.drafts).toBeDefined();
    expect(instance.underOffer).toBeDefined();
    expect(instance.sold).toBeDefined();
  });

  it("struct/AgentSummary/passes_validation", async () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(AgentSummary, payload);
    const errors = await validate(instance);
    expect(errors.length).toBe(0);
  });

  it("struct/AgentSummary/onTheMarket/required", async () => {
    const payload = buildValidPayload();
    delete payload.onTheMarket;
    const instance = plainToInstance(AgentSummary, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/AgentSummary/drafts/required", async () => {
    const payload = buildValidPayload();
    delete payload.drafts;
    const instance = plainToInstance(AgentSummary, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/AgentSummary/underOffer/required", async () => {
    const payload = buildValidPayload();
    delete payload.underOffer;
    const instance = plainToInstance(AgentSummary, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/AgentSummary/sold/required", async () => {
    const payload = buildValidPayload();
    delete payload.sold;
    const instance = plainToInstance(AgentSummary, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/AgentSummary/serialization_round_trip", () => {
    const instance = plainToInstance(AgentSummary, buildValidPayload());
    const restored = plainToInstance(AgentSummary, instanceToPlain(instance));
    expect(restored).toEqual(instance);
  });
});
