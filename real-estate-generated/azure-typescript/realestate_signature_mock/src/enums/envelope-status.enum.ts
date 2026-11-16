import { EnumStoredType } from '../support/enum-stored-type';

export enum EnvelopeStatus {
  Sent = 'Sent',
  Signed = 'Signed',
  Declined = 'Declined',
}

/**
 * How EnvelopeStatus is stored. Each member's value above is its WIRE value; the database
 * holds the label paired with it here, and a stored label no member maps to fails on read.
 */
export const EnvelopeStatusStorage = new EnumStoredType<EnvelopeStatus>('EnvelopeStatus', [
  [EnvelopeStatus.Sent, 'sent'],
  [EnvelopeStatus.Signed, 'signed'],
  [EnvelopeStatus.Declined, 'declined'],
]);
