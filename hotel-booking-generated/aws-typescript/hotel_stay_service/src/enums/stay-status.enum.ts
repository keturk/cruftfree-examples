import { EnumStoredType } from '../support/enum-stored-type';

export enum StayStatus {
  Held = 'Held',
  Confirmed = 'Confirmed',
  CheckedIn = 'CheckedIn',
  CheckedOut = 'CheckedOut',
  Cancelled = 'Cancelled',
  Expired = 'Expired',
}

/**
 * How StayStatus is stored. Each member's value above is its WIRE value; the database
 * holds the label paired with it here, and a stored label no member maps to fails on read.
 */
export const StayStatusStorage = new EnumStoredType<StayStatus>('StayStatus', [
  [StayStatus.Held, 'held'],
  [StayStatus.Confirmed, 'confirmed'],
  [StayStatus.CheckedIn, 'checked_in'],
  [StayStatus.CheckedOut, 'checked_out'],
  [StayStatus.Cancelled, 'cancelled'],
  [StayStatus.Expired, 'expired'],
]);
