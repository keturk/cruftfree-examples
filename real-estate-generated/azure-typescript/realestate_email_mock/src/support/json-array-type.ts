import { JsonType } from '@mikro-orm/core';
import type { Platform, TransformContext } from '@mikro-orm/core';

/**
 * Persists a `Set` as a JSON array and refuses anything else, in both directions.
 *
 * A `Set<T>` field is stored and carried as a JSON array whose values are unique
 * (uniqueness is enforced where a request enters the service). A `Set` object
 * serializes to `{}`, so a column holding a non-array value holds a lost or corrupted
 * collection; reading it as an empty array would hide that.
 *
 * Both directions are fail-closed: a value that is not an array throws instead of being
 * stored or surfacing as a value the type system believes is an array. The message names
 * the property only; it never echoes the value.
 */
export class JsonArrayType extends JsonType {
  constructor(private readonly propertyPath: string) {
    super();
  }

  /** Distinct per property: MikroORM records the type's name as the property's type. */
  override get name(): string {
    return `JsonArrayType(${this.propertyPath})`;
  }

  override convertToDatabaseValue(
    value: unknown,
    platform: Platform,
    context?: TransformContext,
  ): string | null {
    if (value === null || value === undefined) {
      return super.convertToDatabaseValue(value, platform, context);
    }
    if (!Array.isArray(value)) {
      throw new Error(`${this.propertyPath}: the value to store is not an array`);
    }
    return super.convertToDatabaseValue(value, platform, context);
  }

  override convertToJSValue(
    value: unknown,
    platform: Platform,
    context?: TransformContext,
  ): unknown {
    const converted: unknown = super.convertToJSValue(value, platform, context);
    if (converted === null || converted === undefined) {
      return converted;
    }
    if (!Array.isArray(converted)) {
      throw new Error(`${this.propertyPath}: the stored value is not a JSON array`);
    }
    return converted;
  }
}
