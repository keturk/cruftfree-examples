import { EnumStoredType } from '../support/enum-stored-type';

export enum DeliveryStatus {
  Delivered = 'Delivered',
  Bounced = 'Bounced',
}

/**
 * How DeliveryStatus is stored. Each member's value above is its WIRE value; the database
 * holds the label paired with it here, and a stored label no member maps to fails on read.
 */
export const DeliveryStatusStorage = new EnumStoredType<DeliveryStatus>('DeliveryStatus', [
  [DeliveryStatus.Delivered, 'delivered'],
  [DeliveryStatus.Bounced, 'bounced'],
]);
