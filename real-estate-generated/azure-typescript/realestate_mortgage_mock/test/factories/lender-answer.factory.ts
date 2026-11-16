import { LenderAnswer } from '../../src/realestate_mortgage_mock/entities/mortgage_db/lender-answer.entity';
import { PreapprovalDecision } from '../../src/enums/preapproval-decision.enum';

/**
 * Build a partial LenderAnswer with sensible defaults for testing.
 * Override any field via the `overrides` parameter.
 */
export function buildLenderAnswer(
  overrides?: Partial<LenderAnswer>,
): Partial<LenderAnswer> {
  return {
    applicantName: 'test',
    amount: '99.99',
    decision: PreapprovalDecision.Approved,
    reference: `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`,
    idempotencyKey: `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`,
    applicantEmail: 'user@example.com',
    ...overrides,
  };
}
