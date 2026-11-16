
import {
  IsBoolean,
  IsDefined,
  IsInt,
  IsNotEmpty,
  IsOptional,
  IsString,
  ValidateBy,
  ValidateIf,
} from 'class-validator';
import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import { Type } from 'class-transformer';

export class CreateNoticeDto {

  @ApiProperty()
  @IsDefined()
  @IsString()
  @IsNotEmpty()
  @ValidateBy({ name: 'maxLength', validator: { validate: (value: unknown): boolean => typeof value === 'string' && Array.from(value).length <= 200, defaultMessage: (): string => '$property must be at most 200 characters long' } })
  recipient!: string;

  @ApiProperty()
  @IsDefined()
  @IsString()
  @IsNotEmpty()
  @ValidateBy({ name: 'maxLength', validator: { validate: (value: unknown): boolean => typeof value === 'string' && Array.from(value).length <= 200, defaultMessage: (): string => '$property must be at most 200 characters long' } })
  subject!: string;

  @ApiProperty()
  @IsDefined()
  @IsString()
  @IsNotEmpty()
  @ValidateBy({ name: 'maxLength', validator: { validate: (value: unknown): boolean => typeof value === 'string' && Array.from(value).length <= 2000, defaultMessage: (): string => '$property must be at most 2000 characters long' } })
  body!: string;

  @ApiPropertyOptional()
  @ValidateIf((_object, value) => value !== undefined)
  @IsDefined()
  @IsBoolean()
  delivered?: boolean = false;

  @ApiPropertyOptional()
  @ValidateIf((_object, value) => value !== undefined)
  @IsDefined()
  @IsInt()
  attempts?: number = 0;

  @ApiProperty()
  @IsDefined()
  @IsString()
  @IsNotEmpty()
  @ValidateBy({ name: 'maxLength', validator: { validate: (value: unknown): boolean => typeof value === 'string' && Array.from(value).length <= 120, defaultMessage: (): string => '$property must be at most 120 characters long' } })
  noticeKey!: string;
}
