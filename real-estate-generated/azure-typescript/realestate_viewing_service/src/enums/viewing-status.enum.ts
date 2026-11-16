import { EnumStoredType } from '../support/enum-stored-type';

export enum ViewingStatus {
  Requested = 'Requested',
  Confirmed = 'Confirmed',
  Completed = 'Completed',
  Cancelled = 'Cancelled',
  NoShow = 'NoShow',
}

/**
 * How ViewingStatus is stored. Each member's value above is its WIRE value; the database
 * holds the label paired with it here, and a stored label no member maps to fails on read.
 */
export const ViewingStatusStorage = new EnumStoredType<ViewingStatus>('ViewingStatus', [
  [ViewingStatus.Requested, 'requested'],
  [ViewingStatus.Confirmed, 'confirmed'],
  [ViewingStatus.Completed, 'completed'],
  [ViewingStatus.Cancelled, 'cancelled'],
  [ViewingStatus.NoShow, 'no_show'],
]);
