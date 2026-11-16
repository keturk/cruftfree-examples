import { EnumStoredType } from '../support/enum-stored-type';

export enum OfferStatus {
  Submitted = 'Submitted',
  Accepted = 'Accepted',
  Rejected = 'Rejected',
  Withdrawn = 'Withdrawn',
}

/**
 * How OfferStatus is stored. Each member's value above is its WIRE value; the database
 * holds the label paired with it here, and a stored label no member maps to fails on read.
 */
export const OfferStatusStorage = new EnumStoredType<OfferStatus>('OfferStatus', [
  [OfferStatus.Submitted, 'submitted'],
  [OfferStatus.Accepted, 'accepted'],
  [OfferStatus.Rejected, 'rejected'],
  [OfferStatus.Withdrawn, 'withdrawn'],
]);
