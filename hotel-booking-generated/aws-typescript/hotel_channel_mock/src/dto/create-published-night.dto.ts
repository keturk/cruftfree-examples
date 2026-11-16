
import {
  IsDate,
  IsDefined,
  IsInt,
  IsNotEmpty,
  IsOptional,
  IsString,
  Matches,
  ValidateBy,
} from 'class-validator';
import { ApiProperty, ApiSchema } from '@nestjs/swagger';
import { Transform, Type } from 'class-transformer';

@ApiSchema({ description: 'What the travel sites currently believe about one room type on one night.' })
export class CreatePublishedNightDto {

  @ApiProperty()
  @IsDefined()
  @IsString()
  @IsNotEmpty()
  @ValidateBy({ name: 'maxLength', validator: { validate: (value: unknown): boolean => typeof value === 'string' && Array.from(value).length <= 80, defaultMessage: (): string => '$property must be at most 80 characters long' } })
  roomType!: string;

  @ApiProperty()
  @IsDefined()
  @IsDate()
  @Type(() => Date)
  night!: string;

  @ApiProperty()
  @IsDefined()
  @IsInt()
  left!: number;

  @ApiProperty()
  @IsDefined()
  @Transform(({ value }) => (typeof value === 'number' ? String(value) : value))
  @Matches(/^[+-]?([0-9]+(\.[0-9]*)?|\.[0-9]+)([eE][+-]?[0-9]+)?$/, { message: '$property must be a decimal number' })
  nightlyRate!: DecimalString;

  @ApiProperty()
  @IsDefined()
  @IsDate()
  @Type(() => Date)
  receivedAt!: Date;
}
