import { Type } from '@mikro-orm/core';
import type { EntityProperty, Platform } from '@mikro-orm/core';

/**
 * Persists an enum under its STORED label while the application holds its WIRE value.
 *
 * A generated enum's members carry their wire value -- what a client sends and a
 * response returns, and what request validation accepts. The database holds a different
 * label for a member that declares no `value(...)`: its snake_case name. MikroORM binds
 * an enum column to the values of the enum it is given, so without this type the one
 * spelling would have to serve both and the wire and the database could not each follow
 * their own rule.
 *
 * Reading is fail-closed: a stored label no member maps to throws instead of surfacing
 * as a value the type system believes is a member. The message names the enum only; it
 * never echoes the label or lists the members.
 */
export class EnumStoredType<E extends string> extends Type<
  E | null | undefined,
  string | null | undefined
> {
  /** The stored label of every member, in declaration order: what the column's type is created with. */
  readonly labels: string[];
  private readonly storedByWire: ReadonlyMap<string, string>;
  private readonly wireByStored: ReadonlyMap<string, E>;

  constructor(
    private readonly enumName: string,
    members: ReadonlyArray<readonly [E, string]>,
  ) {
    super();
    this.labels = members.map(([, stored]) => stored);
    this.storedByWire = new Map<string, string>(members);
    this.wireByStored = new Map<string, E>(members.map(([wire, stored]) => [stored, wire]));
  }

  /** Distinct per enum: MikroORM records the type's name as the property's type. */
  override get name(): string {
    return `EnumStoredType(${this.enumName})`;
  }

  override convertToDatabaseValue(value: E | null | undefined): string | null | undefined {
    if (value === null || value === undefined) {
      return value;
    }
    const stored = this.storedByWire.get(value);
    if (stored === undefined) {
      throw new Error(`${this.enumName}: the value is not a member of this enum`);
    }
    return stored;
  }

  override convertToJSValue(value: string | null | undefined): E | null | undefined {
    if (value === null || value === undefined) {
      return value;
    }
    const wire = this.wireByStored.get(value);
    if (wire === undefined) {
      throw new Error(`${this.enumName}: the stored label is not a member of this enum`);
    }
    return wire;
  }

  override compareAsType(): string {
    return 'string';
  }

  override getColumnType(prop: EntityProperty, platform: Platform): string {
    if (!platform.supportsNativeEnums()) {
      return 'enum';
    }
    const nativeName = prop.nativeEnumName;
    if (nativeName === undefined) {
      throw new Error(`${this.enumName}: a native enum column must declare nativeEnumName`);
    }
    const schema = this.meta?.schema;
    const qualified =
      schema !== undefined &&
      schema !== platform.getDefaultSchemaName() &&
      !nativeName.includes('.');
    return qualified ? `${schema}.${nativeName}` : nativeName;
  }
}
