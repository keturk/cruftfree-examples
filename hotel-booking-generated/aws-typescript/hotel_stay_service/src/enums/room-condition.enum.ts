import { EnumStoredType } from '../support/enum-stored-type';

export enum RoomCondition {
  Ready = 'Ready',
  Dirty = 'Dirty',
  OutOfService = 'OutOfService',
}

/**
 * How RoomCondition is stored. Each member's value above is its WIRE value; the database
 * holds the label paired with it here, and a stored label no member maps to fails on read.
 */
export const RoomConditionStorage = new EnumStoredType<RoomCondition>('RoomCondition', [
  [RoomCondition.Ready, 'ready'],
  [RoomCondition.Dirty, 'dirty'],
  [RoomCondition.OutOfService, 'out_of_service'],
]);
