import { EnumStoredType } from '../support/enum-stored-type';

export enum ContractStatus {
  AwaitingSignature = 'AwaitingSignature',
  Signed = 'Signed',
  Declined = 'Declined',
}

/**
 * How ContractStatus is stored. Each member's value above is its WIRE value; the database
 * holds the label paired with it here, and a stored label no member maps to fails on read.
 */
export const ContractStatusStorage = new EnumStoredType<ContractStatus>('ContractStatus', [
  [ContractStatus.AwaitingSignature, 'awaiting_signature'],
  [ContractStatus.Signed, 'signed'],
  [ContractStatus.Declined, 'declined'],
]);
