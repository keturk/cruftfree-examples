
import {
  IsArray,
  IsBoolean,
  IsDate,
  IsDefined,
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

@ApiSchema({ description: 'API keys the vendor issued. Only the SHA-256 hash of a key is stored.' })
export class UpdateApiKeyDto {

  @ApiPropertyOptional()
  @ValidateIf((_object, value) => value !== undefined)
  @IsDefined()
  @IsString()
  @IsNotEmpty()
  @ValidateBy({ name: 'maxLength', validator: { validate: (value: unknown): boolean => typeof value === 'string' && Array.from(value).length <= 64, defaultMessage: (): string => '$property must be at most 64 characters long' } })
  keyHash?: string;

  @ApiPropertyOptional({ format: 'uuid' })
  @ValidateIf((_object, value) => value !== undefined)
  @IsDefined()
  @MinLength(36)
  @MaxLength(36)
  @Matches(new RegExp("^(?:[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12})$", "u"))
  ownerId?: string;

  @ApiPropertyOptional()
  @ValidateIf((_object, value) => value !== undefined)
  @IsDefined()
  @IsArray()
  @IsString({ each: true })
  scopes?: string[];

  @ApiPropertyOptional()
  @ValidateIf((_object, value) => value !== undefined)
  @IsDefined()
  @IsBoolean()
  isActive?: boolean;

  @ApiPropertyOptional()
  @IsOptional()
  @IsDate()
  @Type(() => Date)
  expiresAt?: Date | null;

  @ApiPropertyOptional()
  @IsOptional()
  @IsDate()
  @Type(() => Date)
  lastUsedAt?: Date | null;
}

export class ApiKeyBatchUpdateItemDto extends UpdateApiKeyDto {
  @ApiProperty({ format: 'uuid' })
  @IsDefined()
  @MinLength(36)
  @MaxLength(36)
  @Matches(new RegExp("^(?:[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12})$", "u"))
  id!: string;
}
