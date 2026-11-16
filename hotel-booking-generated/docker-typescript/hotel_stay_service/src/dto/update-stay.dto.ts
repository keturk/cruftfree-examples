
import {
  IsDate,
  IsDefined,
  IsEnum,
  IsInt,
  IsNotEmpty,
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
import { StayStatus } from '../enums/stay-status.enum';

export class UpdateStayDto {

  @ApiPropertyOptional({ description: 'MH-402193. The code a guest reads out at the desk.' })
  @ValidateIf((_object, value) => value !== undefined)
  @IsDefined()
  @IsString()
  @IsNotEmpty()
  @ValidateBy({ name: 'maxLength', validator: { validate: (value: unknown): boolean => typeof value === 'string' && Array.from(value).length <= 20, defaultMessage: (): string => '$property must be at most 20 characters long' } })
  code?: string;

  @ApiPropertyOptional({ format: 'uuid' })
  @ValidateIf((_object, value) => value !== undefined)
  @IsDefined()
  @MinLength(36)
  @MaxLength(36)
  @Matches(new RegExp("^(?:[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12})$", "u"))
  roomTypeId?: string;

  @ApiPropertyOptional()
  @ValidateIf((_object, value) => value !== undefined)
  @IsDefined()
  @IsString()
  @IsNotEmpty()
  @ValidateBy({ name: 'maxLength', validator: { validate: (value: unknown): boolean => typeof value === 'string' && Array.from(value).length <= 80, defaultMessage: (): string => '$property must be at most 80 characters long' } })
  roomTypeName?: string;

  @ApiPropertyOptional()
  @IsOptional()
  @IsString()
  @ValidateBy({ name: 'maxLength', validator: { validate: (value: unknown): boolean => typeof value === 'string' && Array.from(value).length <= 8, defaultMessage: (): string => '$property must be at most 8 characters long' } })
  roomNumber?: string | null;

  @ApiPropertyOptional()
  @ValidateIf((_object, value) => value !== undefined)
  @IsDefined()
  @IsString()
  @IsNotEmpty()
  @ValidateBy({ name: 'maxLength', validator: { validate: (value: unknown): boolean => typeof value === 'string' && Array.from(value).length <= 64, defaultMessage: (): string => '$property must be at most 64 characters long' } })
  guestId?: string;

  @ApiPropertyOptional()
  @ValidateIf((_object, value) => value !== undefined)
  @IsDefined()
  @IsString()
  @IsNotEmpty()
  @ValidateBy({ name: 'maxLength', validator: { validate: (value: unknown): boolean => typeof value === 'string' && Array.from(value).length <= 200, defaultMessage: (): string => '$property must be at most 200 characters long' } })
  guestName?: string;

  @ApiPropertyOptional({ pattern: "^(?:[!#-'*-+\\-/-9=?A-Z\\^-~]+(?:\\.[!#-'*-+\\-/-9=?A-Z\\^-~]+)*@(?:[0-9](?:-*[0-9A-Za-z])*\\.(?:[0-9](?:-*[0-9A-Za-z])*\\.)*[A-Za-z]+(?:(?:(?:[0-9]|-+[0-9A-Za-z])(?:-*[0-9A-Za-z])*)?\\.(?:[0-9](?:-*[0-9A-Za-z])*\\.)*[A-Za-z]+)*|[A-Za-z]+(?:(?:(?:[0-9]|-+[0-9A-Za-z])(?:-*[0-9A-Za-z])*)?\\.(?:[0-9](?:-*[0-9A-Za-z])*\\.)*[A-Za-z]+)+))$" })
  @ValidateIf((_object, value) => value !== undefined)
  @IsDefined()
  @MinLength(1)
  @MaxLength(254)
  @Matches(new RegExp("^(?:[!#-'*-+\\-/-9=?A-Z\\^-~]+(?:\\.[!#-'*-+\\-/-9=?A-Z\\^-~]+)*@(?:[0-9](?:-*[0-9A-Za-z])*\\.(?:[0-9](?:-*[0-9A-Za-z])*\\.)*[A-Za-z]+(?:(?:(?:[0-9]|-+[0-9A-Za-z])(?:-*[0-9A-Za-z])*)?\\.(?:[0-9](?:-*[0-9A-Za-z])*\\.)*[A-Za-z]+)*|[A-Za-z]+(?:(?:(?:[0-9]|-+[0-9A-Za-z])(?:-*[0-9A-Za-z])*)?\\.(?:[0-9](?:-*[0-9A-Za-z])*\\.)*[A-Za-z]+)+))$", "u"))
  @ValidateBy({ name: 'isEmailAddressLengths', validator: { validate: (value: unknown): boolean => { if (typeof value !== 'string') { return false; } const at = value.lastIndexOf('@'); const length = Array.from(value.slice(0, Math.max(at, 0))).length; return length >= 1 && length <= 64 && ((value: unknown): boolean => { if (typeof value !== 'string') { return false; } const labels = value.split('.'); const topLevel = Array.from(labels[labels.length - 1] ?? '').length; return labels.every((label: string): boolean => Array.from(label).length <= 63) && topLevel >= 2 && topLevel <= 63; })(value.slice(at + 1)); }, defaultMessage: (): string => "$property local part must have 1-64 characters, and its domain labels must have at most 63 characters, and the top-level label 2-63" } })
  guestEmail?: string;

  @ApiPropertyOptional()
  @ValidateIf((_object, value) => value !== undefined)
  @IsDefined()
  @IsDate()
  @Type(() => Date)
  arrival?: string;

  @ApiPropertyOptional()
  @ValidateIf((_object, value) => value !== undefined)
  @IsDefined()
  @IsDate()
  @Type(() => Date)
  departure?: string;

  @ApiPropertyOptional()
  @ValidateIf((_object, value) => value !== undefined)
  @IsDefined()
  @IsInt()
  nights?: number;

  @ApiPropertyOptional()
  @ValidateIf((_object, value) => value !== undefined)
  @IsDefined()
  @IsInt()
  guests?: number;

  @ApiPropertyOptional()
  @ValidateIf((_object, value) => value !== undefined)
  @IsDefined()
  @Transform(({ value }) => (typeof value === 'number' ? String(value) : value))
  @Matches(/^[+-]?([0-9]+(\.[0-9]*)?|\.[0-9]+)([eE][+-]?[0-9]+)?$/, { message: '$property must be a decimal number' })
  total?: DecimalString;

  @ApiPropertyOptional({ enum: StayStatus, enumName: 'StayStatus', enumSchema: { description: 'A stay from the first hold to the last goodbye.' } })
  @ValidateIf((_object, value) => value !== undefined)
  @IsDefined()
  @IsEnum(StayStatus)
  status?: StayStatus;

  @ApiPropertyOptional({ description: 'A held room goes back on sale at this moment.' })
  @IsOptional()
  @IsDate()
  @Type(() => Date)
  holdUntil?: Date | null;

  @ApiPropertyOptional()
  @IsOptional()
  @IsString()
  @ValidateBy({ name: 'maxLength', validator: { validate: (value: unknown): boolean => typeof value === 'string' && Array.from(value).length <= 40, defaultMessage: (): string => '$property must be at most 40 characters long' } })
  chargeId?: string | null;

  @ApiPropertyOptional()
  @IsOptional()
  @IsString()
  deskNote?: string | null;
}

export class StayBatchUpdateItemDto extends UpdateStayDto {
  @ApiProperty({ format: 'uuid' })
  @IsDefined()
  @MinLength(36)
  @MaxLength(36)
  @Matches(new RegExp("^(?:[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12})$", "u"))
  id!: string;
}
