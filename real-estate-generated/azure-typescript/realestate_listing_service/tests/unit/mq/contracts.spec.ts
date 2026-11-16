/**
 * Tests for event contract validation (auto-generated).
 */
import { _decimalEquals } from '../realestate_listing_service/_decimalHelpers';
import { validateListingPriceChangedContract } from '../../../src/mq/contracts';
import { ContractViolationError } from '../../../src/errors/contract-violation';

describe('ListingPriceChanged contracts', () => {
  it("pubsub_contract/mq/ListingPriceChanged/accepts_valid_payload", () => {
    expect(() =>
      validateListingPriceChangedContract(
        '00000000-0000-4000-8000-000000000001',
        'test',
        '99.99',
        '99.992',
      ),
    ).not.toThrow();
  });

  it("pubsub_contract/mq/ListingPriceChanged/0/rejects_violated_clause", () => {
    expect(() =>
      validateListingPriceChangedContract(
        '00000000-0000-4000-8000-000000000001',
        'test',
        '99.99',
        '99.99',
      ),
    ).toThrow(ContractViolationError);
  });

});

