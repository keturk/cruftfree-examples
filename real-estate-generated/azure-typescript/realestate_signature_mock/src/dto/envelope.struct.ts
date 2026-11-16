import {
  IsEnum,
  IsNotEmpty,
  IsString,
  ValidateBy,
} from 'class-validator';
import { ApiProperty } from '@nestjs/swagger';
import { EnvelopeStatus } from '../enums/envelope-status.enum'

export class Envelope {

  @ApiProperty()
  @IsString()
  @IsNotEmpty()
  @ValidateBy({ name: 'maxLength', validator: { validate: (value: unknown): boolean => typeof value === 'string' && Array.from(value).length <= 40, defaultMessage: (): string => '$property must be at most 40 characters long' } })
  id!: string;

  @ApiProperty({ enum: EnvelopeStatus, enumName: 'EnvelopeStatus' })
  @IsEnum(EnvelopeStatus)
  status!: EnvelopeStatus;


}
