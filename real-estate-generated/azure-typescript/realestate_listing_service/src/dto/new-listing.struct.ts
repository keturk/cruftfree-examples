import {
  IsEnum,
  IsInt,
  IsNotEmpty,
  IsString,
  Matches,
  MaxLength,
  MinLength,
  ValidateBy,
} from 'class-validator';
import { ApiProperty } from '@nestjs/swagger';
import { Transform } from 'class-transformer';
import { PropertyKind } from '../enums/property-kind.enum'

export class NewListing {

  @ApiProperty()
  @IsString()
  @IsNotEmpty()
  @ValidateBy({ name: 'maxLength', validator: { validate: (value: unknown): boolean => typeof value === 'string' && Array.from(value).length <= 200, defaultMessage: (): string => '$property must be at most 200 characters long' } })
  title!: string;

  @ApiProperty({ format: 'uuid' })
  @MinLength(36)
  @MaxLength(36)
  @Matches(new RegExp("^(?:[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12})$", "u"))
  neighbourhoodId!: string;

  @ApiProperty({ enum: PropertyKind, enumName: 'PropertyKind' })
  @IsEnum(PropertyKind)
  kind!: PropertyKind;

  @ApiProperty()
  @Transform(({ value }) => (typeof value === 'number' ? String(value) : value))
  @Matches(/^[+-]?([0-9]+(\.[0-9]*)?|\.[0-9]+)([eE][+-]?[0-9]+)?$/, { message: '$property must be a decimal number' })
  price!: DecimalString;

  @ApiProperty()
  @IsInt()
  bedrooms!: number;

  @ApiProperty()
  @IsInt()
  bathrooms!: number;

  @ApiProperty()
  @IsInt()
  areaSqm!: number;

  @ApiProperty()
  @IsString()
  @IsNotEmpty()
  summary!: string;


}
