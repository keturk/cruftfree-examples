import { EnumStoredType } from '../support/enum-stored-type';

export enum PropertyKind {
  House = 'House',
  Apartment = 'Apartment',
  Townhouse = 'Townhouse',
  Cottage = 'Cottage',
  Land = 'Land',
}

/**
 * How PropertyKind is stored. Each member's value above is its WIRE value; the database
 * holds the label paired with it here, and a stored label no member maps to fails on read.
 */
export const PropertyKindStorage = new EnumStoredType<PropertyKind>('PropertyKind', [
  [PropertyKind.House, 'house'],
  [PropertyKind.Apartment, 'apartment'],
  [PropertyKind.Townhouse, 'townhouse'],
  [PropertyKind.Cottage, 'cottage'],
  [PropertyKind.Land, 'land'],
]);
