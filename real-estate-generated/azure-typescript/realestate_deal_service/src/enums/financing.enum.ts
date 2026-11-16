import { EnumStoredType } from '../support/enum-stored-type';

export enum Financing {
  Cash = 'Cash',
  Mortgage = 'Mortgage',
}

/**
 * How Financing is stored. Each member's value above is its WIRE value; the database
 * holds the label paired with it here, and a stored label no member maps to fails on read.
 */
export const FinancingStorage = new EnumStoredType<Financing>('Financing', [
  [Financing.Cash, 'cash'],
  [Financing.Mortgage, 'mortgage'],
]);
