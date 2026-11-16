
import {
  IsDate,
  IsDefined,
  IsEnum,
  IsInt,
  IsNotEmpty,
  IsNumber,
  IsOptional,
  IsString,
  Matches,
  MaxLength,
  MinLength,
  ValidateBy,
  ValidateIf,
} from 'class-validator';
import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import { Transform, Type } from 'class-transformer';
import { PropertyKind } from '../enums/property-kind.enum';
import { ListingStatus } from '../enums/listing-status.enum';

export class CreateListingDto {

  @ApiProperty()
  @IsDefined()
  @IsString()
  @IsNotEmpty()
  @ValidateBy({ name: 'maxLength', validator: { validate: (value: unknown): boolean => typeof value === 'string' && Array.from(value).length <= 200, defaultMessage: (): string => '$property must be at most 200 characters long' } })
  title!: string;

  @ApiProperty()
  @IsDefined()
  @IsString()
  @IsNotEmpty()
  @ValidateBy({ name: 'maxLength', validator: { validate: (value: unknown): boolean => typeof value === 'string' && Array.from(value).length <= 120, defaultMessage: (): string => '$property must be at most 120 characters long' } })
  neighbourhoodName!: string;

  @ApiProperty({ enum: PropertyKind, enumName: 'PropertyKind' })
  @IsDefined()
  @IsEnum(PropertyKind)
  kind!: PropertyKind;

  @ApiProperty()
  @IsDefined()
  @Transform(({ value }) => (typeof value === 'number' ? String(value) : value))
  @Matches(/^[+-]?([0-9]+(\.[0-9]*)?|\.[0-9]+)([eE][+-]?[0-9]+)?$/, { message: '$property must be a decimal number' })
  price!: DecimalString;

  @ApiProperty()
  @IsDefined()
  @IsInt()
  bedrooms!: number;

  @ApiProperty()
  @IsDefined()
  @IsInt()
  bathrooms!: number;

  @ApiProperty()
  @IsDefined()
  @IsInt()
  areaSqm!: number;

  @ApiPropertyOptional({ enum: ListingStatus, enumName: 'ListingStatus', enumSchema: { description: 'Where a home is in being sold. An offer and a viewing are only taken while it is Active.' } })
  @ValidateIf((_object, value) => value !== undefined)
  @IsDefined()
  @IsEnum(ListingStatus)
  status?: ListingStatus = ListingStatus.Draft;

  @ApiProperty()
  @IsDefined()
  @IsString()
  @IsNotEmpty()
  @ValidateBy({ name: 'maxLength', validator: { validate: (value: unknown): boolean => typeof value === 'string' && Array.from(value).length <= 200, defaultMessage: (): string => '$property must be at most 200 characters long' } })
  agentName!: string;

  @ApiPropertyOptional()
  @IsOptional()
  @IsDate()
  @Type(() => Date)
  publishedAt?: Date | null;

  @ApiProperty()
  @IsDefined()
  @IsString()
  @IsNotEmpty()
  summary!: string;

  @ApiProperty()
  @IsDefined()
  @IsString()
  @IsNotEmpty()
  @ValidateBy({ name: 'maxLength', validator: { validate: (value: unknown): boolean => typeof value === 'string' && Array.from(value).length <= 120, defaultMessage: (): string => '$property must be at most 120 characters long' } })
  city!: string;

  @ApiProperty()
  @IsDefined()
  @IsNumber()
  latitude!: number;

  @ApiProperty()
  @IsDefined()
  @IsNumber()
  longitude!: number;

  @ApiProperty({ pattern: "^(?:[!#-'*-+\\-/-9=?A-Z\\^-~]+(?:\\.[!#-'*-+\\-/-9=?A-Z\\^-~]+)*@(?:[0-9](?:-*[0-9A-Za-z])*\\.(?:[0-9](?:-*[0-9A-Za-z])*\\.)*[A-Za-z]+(?:(?:(?:[0-9]|-+[0-9A-Za-z])(?:-*[0-9A-Za-z])*)?\\.(?:[0-9](?:-*[0-9A-Za-z])*\\.)*[A-Za-z]+)*|[A-Za-z]+(?:(?:(?:[0-9]|-+[0-9A-Za-z])(?:-*[0-9A-Za-z])*)?\\.(?:[0-9](?:-*[0-9A-Za-z])*\\.)*[A-Za-z]+)+))$" })
  @IsDefined()
  @MinLength(1)
  @MaxLength(254)
  @Matches(new RegExp("^(?:[!#-'*-+\\-/-9=?A-Z\\^-~]+(?:\\.[!#-'*-+\\-/-9=?A-Z\\^-~]+)*@(?:[0-9](?:-*[0-9A-Za-z])*\\.(?:[0-9](?:-*[0-9A-Za-z])*\\.)*[A-Za-z]+(?:(?:(?:[0-9]|-+[0-9A-Za-z])(?:-*[0-9A-Za-z])*)?\\.(?:[0-9](?:-*[0-9A-Za-z])*\\.)*[A-Za-z]+)*|[A-Za-z]+(?:(?:(?:[0-9]|-+[0-9A-Za-z])(?:-*[0-9A-Za-z])*)?\\.(?:[0-9](?:-*[0-9A-Za-z])*\\.)*[A-Za-z]+)+))$", "u"))
  @ValidateBy({ name: 'isEmailAddressLengths', validator: { validate: (value: unknown): boolean => { if (typeof value !== 'string') { return false; } const at = value.lastIndexOf('@'); const length = Array.from(value.slice(0, Math.max(at, 0))).length; return length >= 1 && length <= 64 && ((value: unknown): boolean => { if (typeof value !== 'string') { return false; } const labels = value.split('.'); const topLevel = Array.from(labels[labels.length - 1] ?? '').length; return labels.every((label: string): boolean => Array.from(label).length <= 63) && topLevel >= 2 && topLevel <= 63; })(value.slice(at + 1)); }, defaultMessage: (): string => "$property local part must have 1-64 characters, and its domain labels must have at most 63 characters, and the top-level label 2-63" } })
  agentEmail!: string;
}
