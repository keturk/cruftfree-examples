import { buildLenderAnswer } from './lender-answer.factory';

describe('buildLenderAnswer', () => {
  it("entity_factory/mortgageDb/LenderAnswer/valid_instance", () => {
    const result = buildLenderAnswer();
    expect(result).toBeDefined();
    expect(result.applicantName).toBeDefined();
    expect(result.amount).toBeDefined();
    expect(result.decision).toBeDefined();
    expect(result.reference).toBeDefined();
    expect(result.idempotencyKey).toBeDefined();
    expect(result.applicantEmail).toBeDefined();
  });

  it("entity_factory/mortgageDb/LenderAnswer/applies_overrides", () => {
    const overrides = {
      applicantName: 'test',
    };
    const result = buildLenderAnswer(overrides);
    expect(result.applicantName).toBe(overrides.applicantName);
  });

  it("entity_factory/mortgageDb/LenderAnswer/distinct_instances", () => {
    const a = buildLenderAnswer();
    const b = buildLenderAnswer();
    expect(a).not.toBe(b);
  });
});
