import { EnumStoredType } from '../support/enum-stored-type';

export enum TestCard {
  CardThatPays = 'CardThatPays',
  CardThatIsDeclined = 'CardThatIsDeclined',
}

/**
 * How TestCard is stored. Each member's value above is its WIRE value; the database
 * holds the label paired with it here, and a stored label no member maps to fails on read.
 */
export const TestCardStorage = new EnumStoredType<TestCard>('TestCard', [
  [TestCard.CardThatPays, 'card_that_pays'],
  [TestCard.CardThatIsDeclined, 'card_that_is_declined'],
]);
