import { EnumStoredType } from '../support/enum-stored-type';

export enum PreapprovalDecision {
  Approved = 'Approved',
  Declined = 'Declined',
}

/**
 * How PreapprovalDecision is stored. Each member's value above is its WIRE value; the database
 * holds the label paired with it here, and a stored label no member maps to fails on read.
 */
export const PreapprovalDecisionStorage = new EnumStoredType<PreapprovalDecision>('PreapprovalDecision', [
  [PreapprovalDecision.Approved, 'approved'],
  [PreapprovalDecision.Declined, 'declined'],
]);
