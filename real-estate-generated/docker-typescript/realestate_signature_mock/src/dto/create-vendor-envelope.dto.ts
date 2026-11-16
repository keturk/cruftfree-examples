
import {
  IsDate,
  IsDefined,
  IsEnum,
  IsNotEmpty,
  IsOptional,
  IsString,
  Matches,
  MaxLength,
  MinLength,
  ValidateBy,
  ValidateIf,
} from 'class-validator';
import { ApiProperty, ApiPropertyOptional, ApiSchema } from '@nestjs/swagger';
import { Type } from 'class-transformer';
import { EnvelopeStatus } from '../enums/envelope-status.enum';

@ApiSchema({ description: 'A document waiting for a signature.' })
export class CreateVendorEnvelopeDto {

  @ApiProperty()
  @IsDefined()
  @IsString()
  @IsNotEmpty()
  @ValidateBy({ name: 'maxLength', validator: { validate: (value: unknown): boolean => typeof value === 'string' && Array.from(value).length <= 200, defaultMessage: (): string => '$property must be at most 200 characters long' } })
  signerName!: string;

  @ApiProperty()
  @IsDefined()
  @IsString()
  @IsNotEmpty()
  @ValidateBy({ name: 'maxLength', validator: { validate: (value: unknown): boolean => typeof value === 'string' && Array.from(value).length <= 200, defaultMessage: (): string => '$property must be at most 200 characters long' } })
  documentTitle!: string;

  @ApiPropertyOptional({ enum: EnvelopeStatus, enumName: 'EnvelopeStatus' })
  @ValidateIf((_object, value) => value !== undefined)
  @IsDefined()
  @IsEnum(EnvelopeStatus)
  status?: EnvelopeStatus = EnvelopeStatus.Sent;

  @ApiPropertyOptional()
  @IsOptional()
  @IsDate()
  @Type(() => Date)
  settledAt?: Date | null;

  @ApiProperty()
  @IsDefined()
  @IsString()
  @IsNotEmpty()
  documentBody!: string;

  @ApiProperty({ pattern: "^(?:[!#-'*-+\\-/-9=?A-Z\\^-~]+(?:\\.[!#-'*-+\\-/-9=?A-Z\\^-~]+)*@(?:[0-9](?:-*[0-9A-Za-z])*\\.(?:[0-9](?:-*[0-9A-Za-z])*\\.)*[A-Za-z]+(?:(?:(?:[0-9]|-+[0-9A-Za-z])(?:-*[0-9A-Za-z])*)?\\.(?:[0-9](?:-*[0-9A-Za-z])*\\.)*[A-Za-z]+)*|[A-Za-z]+(?:(?:(?:[0-9]|-+[0-9A-Za-z])(?:-*[0-9A-Za-z])*)?\\.(?:[0-9](?:-*[0-9A-Za-z])*\\.)*[A-Za-z]+)+))$" })
  @IsDefined()
  @MinLength(1)
  @MaxLength(254)
  @Matches(new RegExp("^(?:[!#-'*-+\\-/-9=?A-Z\\^-~]+(?:\\.[!#-'*-+\\-/-9=?A-Z\\^-~]+)*@(?:[0-9](?:-*[0-9A-Za-z])*\\.(?:[0-9](?:-*[0-9A-Za-z])*\\.)*[A-Za-z]+(?:(?:(?:[0-9]|-+[0-9A-Za-z])(?:-*[0-9A-Za-z])*)?\\.(?:[0-9](?:-*[0-9A-Za-z])*\\.)*[A-Za-z]+)*|[A-Za-z]+(?:(?:(?:[0-9]|-+[0-9A-Za-z])(?:-*[0-9A-Za-z])*)?\\.(?:[0-9](?:-*[0-9A-Za-z])*\\.)*[A-Za-z]+)+))$", "u"))
  @ValidateBy({ name: 'isEmailAddressLengths', validator: { validate: (value: unknown): boolean => { if (typeof value !== 'string') { return false; } const at = value.lastIndexOf('@'); const length = Array.from(value.slice(0, Math.max(at, 0))).length; return length >= 1 && length <= 64 && ((value: unknown): boolean => { if (typeof value !== 'string') { return false; } const labels = value.split('.'); const topLevel = Array.from(labels[labels.length - 1] ?? '').length; return labels.every((label: string): boolean => Array.from(label).length <= 63) && topLevel >= 2 && topLevel <= 63; })(value.slice(at + 1)); }, defaultMessage: (): string => "$property local part must have 1-64 characters, and its domain labels must have at most 63 characters, and the top-level label 2-63" } })
  signerEmail!: string;

  @ApiProperty()
  @IsDefined()
  @IsString()
  @IsNotEmpty()
  @ValidateBy({ name: 'maxLength', validator: { validate: (value: unknown): boolean => typeof value === 'string' && Array.from(value).length <= 40, defaultMessage: (): string => '$property must be at most 40 characters long' } })
  envelopeId!: string;

  @ApiProperty()
  @IsDefined()
  @IsString()
  @IsNotEmpty()
  @ValidateBy({ name: 'maxLength', validator: { validate: (value: unknown): boolean => typeof value === 'string' && Array.from(value).length <= 120, defaultMessage: (): string => '$property must be at most 120 characters long' } })
  idempotencyKey!: string;
}
