import { EnumStoredType } from '../support/enum-stored-type';

export enum ListingStatus {
  Draft = 'Draft',
  Active = 'Active',
  UnderOffer = 'UnderOffer',
  Sold = 'Sold',
  Withdrawn = 'Withdrawn',
}

/**
 * How ListingStatus is stored. Each member's value above is its WIRE value; the database
 * holds the label paired with it here, and a stored label no member maps to fails on read.
 */
export const ListingStatusStorage = new EnumStoredType<ListingStatus>('ListingStatus', [
  [ListingStatus.Draft, 'draft'],
  [ListingStatus.Active, 'active'],
  [ListingStatus.UnderOffer, 'under_offer'],
  [ListingStatus.Sold, 'sold'],
  [ListingStatus.Withdrawn, 'withdrawn'],
]);
