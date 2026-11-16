/**
 * Exact Decimal and Money arithmetic for generated code.
 *
 * A DSL `Decimal` or `Money` value is held as its decimal text (`DecimalString`): the form a
 * NUMERIC column is read in and the JSON wire carries it as. Every operation on one runs here, on
 * decimal.js under the DSL's decimal context -- 28 significant digits,
 * ties rounded to the even neighbour, the context every target computes in -- so a value never
 * passes through a binary double: 0.1 + 0.2 is 0.3. Text that is not a decimal, or a number that is
 * not finite, is refused, never computed as NaN.
 */
import DecimalJs from 'decimal.js';

declare global {
  /** A DSL `Decimal`/`Money` value: its exact decimal text. */
  type DecimalString = string;
}

/**
 * A decimal operand: decimal text, a number (read as its shortest round-trip text), or a
 * `bigint` (a DSL `Long`, read exactly).
 */
export type DecimalOperand = DecimalString | number | bigint;

const ExactDecimal = DecimalJs.clone({
  precision: 28,
  rounding: DecimalJs.ROUND_HALF_EVEN,
});

/** Optional sign, digits with an optional fraction, optional exponent. */
const DECIMAL_TEXT = /^[+-]?([0-9]+(\.[0-9]*)?|\.[0-9]+)([eE][+-]?[0-9]+)?$/;

function exact(value: DecimalOperand): DecimalJs {
  if (typeof value === 'bigint') {
    return new ExactDecimal(value.toString());
  }
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) {
      throw new RangeError(`A decimal operation received the number ${value}, which is not finite.`);
    }
    return new ExactDecimal(String(value));
  }
  if (!DECIMAL_TEXT.test(value)) {
    throw new RangeError(`A decimal operation received '${value}', which is not decimal text.`);
  }
  return new ExactDecimal(value);
}

function text(value: DecimalJs): DecimalString {
  return value.toFixed();
}

function nonZeroDivisor(value: DecimalOperand): DecimalJs {
  const divisor = exact(value);
  if (divisor.isZero()) {
    throw new RangeError('Decimal division by zero.');
  }
  return divisor;
}

function nonEmpty(values: readonly DecimalOperand[], operation: string): readonly DecimalOperand[] {
  if (values.length === 0) {
    throw new RangeError(`Decimal ${operation} of no values.`);
  }
  return values;
}

/**
 * The exact decimal *value* is (`Money.of`, `Decimal.parse`, a number into a decimal slot).
 * An absent value stays absent.
 */
export function _decimalOf(value: DecimalOperand): DecimalString;
export function _decimalOf(value: DecimalOperand | null | undefined): DecimalString | null;
export function _decimalOf(value: DecimalOperand | null | undefined): DecimalString | null {
  return value === null || value === undefined ? null : text(exact(value));
}

export function _decimalAdd(left: DecimalOperand, right: DecimalOperand): DecimalString {
  return text(exact(left).plus(exact(right)));
}

export function _decimalSub(left: DecimalOperand, right: DecimalOperand): DecimalString {
  return text(exact(left).minus(exact(right)));
}

export function _decimalMul(left: DecimalOperand, right: DecimalOperand): DecimalString {
  return text(exact(left).times(exact(right)));
}

export function _decimalDiv(left: DecimalOperand, right: DecimalOperand): DecimalString {
  return text(exact(left).div(nonZeroDivisor(right)));
}

/** The remainder, with the dividend's sign. */
export function _decimalMod(left: DecimalOperand, right: DecimalOperand): DecimalString {
  return text(exact(left).mod(nonZeroDivisor(right)));
}

export function _decimalPow(base: DecimalOperand, exponent: DecimalOperand): DecimalString {
  return text(exact(base).pow(exact(exponent)));
}

export function _decimalNeg(value: DecimalOperand): DecimalString {
  return text(exact(value).neg());
}

export function _decimalAbs(value: DecimalOperand): DecimalString {
  return text(exact(value).abs());
}

/** Negative, zero or positive as *left* is less than, equal to or greater than *right*. */
export function _decimalCompare(left: DecimalOperand, right: DecimalOperand): number {
  return exact(left).cmp(exact(right));
}

/** Whether *left* and *right* hold the same value; an absent value equals only another. */
export function _decimalEquals(
  left: DecimalOperand | null | undefined,
  right: DecimalOperand | null | undefined,
): boolean {
  if (left === null || left === undefined || right === null || right === undefined) {
    return (left === null || left === undefined) && (right === null || right === undefined);
  }
  return exact(left).eq(exact(right));
}

export function _decimalMin(...values: DecimalOperand[]): DecimalString {
  return text(nonEmpty(values, 'min').map(exact).reduce((a, b) => (b.lt(a) ? b : a)));
}

export function _decimalMax(...values: DecimalOperand[]): DecimalString {
  return text(nonEmpty(values, 'max').map(exact).reduce((a, b) => (b.gt(a) ? b : a)));
}

export function _decimalSum(values: readonly DecimalOperand[]): DecimalString {
  return text(values.reduce<DecimalJs>((total, value) => total.plus(exact(value)), new ExactDecimal(0)));
}

export function _decimalAvg(values: readonly DecimalOperand[]): DecimalString {
  return _decimalDiv(_decimalSum(nonEmpty(values, 'average')), values.length);
}

export function _decimalClamp(value: DecimalOperand, low: DecimalOperand, high: DecimalOperand): DecimalString {
  return _decimalMax(low, _decimalMin(high, value));
}

/** `Math.round(value)`: the nearest integer, a tie to the even one. */
export function _decimalRoundToInteger(value: DecimalOperand): number {
  return Number(exact(value).toDecimalPlaces(0, DecimalJs.ROUND_HALF_EVEN).toFixed());
}

/** `Math.round(value, places)`: *value* to *places* fraction digits (tens, hundreds... when
 * negative), a tie to the even neighbour. */
export function _decimalRound(value: DecimalOperand, places: number): DecimalString {
  if (!Number.isInteger(places)) {
    throw new RangeError(`Decimal rounding needs a whole number of places; got ${places}.`);
  }
  if (places >= 0) {
    return text(exact(value).toDecimalPlaces(places, DecimalJs.ROUND_HALF_EVEN));
  }
  const scale = new ExactDecimal(10).pow(-places);
  return text(exact(value).div(scale).toDecimalPlaces(0, DecimalJs.ROUND_HALF_EVEN).times(scale));
}

export function _decimalFloor(value: DecimalOperand): number {
  return Number(exact(value).floor().toFixed());
}

export function _decimalCeil(value: DecimalOperand): number {
  return Number(exact(value).ceil().toFixed());
}

export function _decimalSign(value: DecimalOperand): number {
  return exact(value).cmp(0);
}

/** `price.toInteger()`: the integer toward zero. */
export function _decimalTruncate(value: DecimalOperand): number {
  return Number(exact(value).trunc().toFixed());
}

/** The nearest double (`Decimal.toFloat`, a decimal into a number slot). An absent value stays absent. */
export function _decimalToNumber(value: DecimalOperand): number;
export function _decimalToNumber(value: DecimalOperand | null | undefined): number | null;
export function _decimalToNumber(value: DecimalOperand | null | undefined): number | null {
  return value === null || value === undefined ? null : Number(text(exact(value)));
}

/** *value* as text, the way a decimal reads in a string: no exponent, no trailing zeros. */
export function _decimalText(value: DecimalOperand): string {
  return text(exact(value));
}

/** *value* with exactly *digits* fraction digits (a `.Nf` format spec), a tie to the even one. */
export function _decimalFixed(value: DecimalOperand, digits: number): string {
  return exact(value).toFixed(digits, DecimalJs.ROUND_HALF_EVEN);
}

/** `Number.format`: *value* with exactly *fractionDigits* fraction digits (a tie to the even
 * one), its integer digits grouped in threes by ',' when *grouping*; locale-neutral. A negative
 * that rounds to zero has no sign. */
export function _decimalFormat(value: DecimalOperand, fractionDigits: number, grouping: boolean): string {
  if (!Number.isInteger(fractionDigits) || fractionDigits < 0) {
    throw new RangeError(`Number.format needs a whole, non-negative number of fraction digits; got ${fractionDigits}.`);
  }
  const fixed = exact(value).toFixed(fractionDigits, DecimalJs.ROUND_HALF_EVEN);
  const negative = fixed.startsWith('-');
  const [whole, fraction] = (negative ? fixed.slice(1) : fixed).split('.');
  const grouped = grouping ? whole.replace(/\B(?=(\d{3})+$)/g, ',') : whole;
  const body = fraction === undefined ? grouped : `${grouped}.${fraction}`;
  return negative && /[1-9]/.test(body) ? `-${body}` : body;
}
