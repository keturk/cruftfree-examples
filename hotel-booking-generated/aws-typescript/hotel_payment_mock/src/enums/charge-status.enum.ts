import { EnumStoredType } from '../support/enum-stored-type';

export enum ChargeStatus {
  Succeeded = 'Succeeded',
  Declined = 'Declined',
  Refunded = 'Refunded',
}

/**
 * How ChargeStatus is stored. Each member's value above is its WIRE value; the database
 * holds the label paired with it here, and a stored label no member maps to fails on read.
 */
export const ChargeStatusStorage = new EnumStoredType<ChargeStatus>('ChargeStatus', [
  [ChargeStatus.Succeeded, 'succeeded'],
  [ChargeStatus.Declined, 'declined'],
  [ChargeStatus.Refunded, 'refunded'],
]);
