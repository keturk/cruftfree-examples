
import {
  IsBoolean,
  IsDefined,
  IsInt,
  IsNotEmpty,
  IsOptional,
  IsString,
  Matches,
  ValidateBy,
  ValidateIf,
} from 'class-validator';
import { ApiProperty, ApiPropertyOptional, ApiSchema } from '@nestjs/swagger';
import { Transform, Type } from 'class-transformer';

@ApiSchema({ description: 'What a guest chooses.' })
export class CreateRoomTypeDto {

  @ApiProperty()
  @IsDefined()
  @IsString()
  @IsNotEmpty()
  @ValidateBy({ name: 'maxLength', validator: { validate: (value: unknown): boolean => typeof value === 'string' && Array.from(value).length <= 80, defaultMessage: (): string => '$property must be at most 80 characters long' } })
  name!: string;

  @ApiProperty()
  @IsDefined()
  @IsString()
  @IsNotEmpty()
  @ValidateBy({ name: 'maxLength', validator: { validate: (value: unknown): boolean => typeof value === 'string' && Array.from(value).length <= 200, defaultMessage: (): string => '$property must be at most 200 characters long' } })
  summary!: string;

  @ApiProperty()
  @IsDefined()
  @IsString()
  @IsNotEmpty()
  description!: string;

  @ApiProperty()
  @IsDefined()
  @IsInt()
  sleeps!: number;

  @ApiProperty()
  @IsDefined()
  @Transform(({ value }) => (typeof value === 'number' ? String(value) : value))
  @Matches(/^[+-]?([0-9]+(\.[0-9]*)?|\.[0-9]+)([eE][+-]?[0-9]+)?$/, { message: '$property must be a decimal number' })
  nightlyRate!: DecimalString;

  @ApiProperty({ description: 'How many rooms of this type can be sold. Taking one out of service does not change it.' })
  @IsDefined()
  @IsInt()
  inventory!: number;

  @ApiPropertyOptional()
  @ValidateIf((_object, value) => value !== undefined)
  @IsDefined()
  @IsBoolean()
  listed?: boolean = true;
}
