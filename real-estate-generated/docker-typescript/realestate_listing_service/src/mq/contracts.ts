/**
 * Event contract validation (auto-generated).
 */
import { ContractViolationError } from '../errors/contract-violation';
import { contractViolationCounter } from './contract-metrics';
import { _decimalEquals } from '../realestate_listing_service/_decimalHelpers';

export function validateListingPriceChangedContract(
  listingId: string,
  title: string,
  oldPrice: DecimalString,
  newPrice: DecimalString,
): void {
  if (!((!_decimalEquals(oldPrice, newPrice)))) {
    console.error('contract_violation', {
      event: 'ListingPriceChanged',
      clause: 'oldPrice != newPrice',
      newPrice,
      oldPrice,
    });
    contractViolationCounter.inc({
      event: 'ListingPriceChanged',
      clause: 'oldPrice != newPrice',
    });
    throw new ContractViolationError({
      event: 'ListingPriceChanged',
      clause: 'oldPrice != newPrice',
      actual: {
        newPrice,
        oldPrice,
      },
    });
  }
}

