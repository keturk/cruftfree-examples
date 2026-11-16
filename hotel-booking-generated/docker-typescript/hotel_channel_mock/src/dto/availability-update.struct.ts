import {
  IsDate,
  IsInt,
  IsNotEmpty,
  IsString,
  Matches,
  ValidateBy,
} from 'class-validator';
import { ApiProperty } from '@nestjs/swagger';
import { Transform, Type } from 'class-transformer';

export class AvailabilityUpdate {

  @ApiProperty()
  @IsString()
  @IsNotEmpty()
  @ValidateBy({ name: 'maxLength', validator: { validate: (value: unknown): boolean => typeof value === 'string' && Array.from(value).length <= 80, defaultMessage: (): string => '$property must be at most 80 characters long' } })
  roomType!: string;

  @ApiProperty()
  @IsDate()
  @Type(() => Date)
  night!: string;

  @ApiProperty()
  @IsInt()
  left!: number;

  @ApiProperty()
  @Transform(({ value }) => (typeof value === 'number' ? String(value) : value))
  @Matches(/^[+-]?([0-9]+(\.[0-9]*)?|\.[0-9]+)([eE][+-]?[0-9]+)?$/, { message: '$property must be a decimal number' })
  nightlyRate!: DecimalString;


}
