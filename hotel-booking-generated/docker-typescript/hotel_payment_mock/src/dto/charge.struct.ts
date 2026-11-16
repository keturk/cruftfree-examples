import {
  IsEnum,
  IsNotEmpty,
  IsOptional,
  IsString,
  ValidateBy,
} from 'class-validator';
import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import { ChargeStatus } from '../enums/charge-status.enum'

export class Charge {

  @ApiProperty()
  @IsString()
  @IsNotEmpty()
  @ValidateBy({ name: 'maxLength', validator: { validate: (value: unknown): boolean => typeof value === 'string' && Array.from(value).length <= 40, defaultMessage: (): string => '$property must be at most 40 characters long' } })
  id!: string;

  @ApiProperty({ enum: ChargeStatus, enumName: 'ChargeStatus' })
  @IsEnum(ChargeStatus)
  status!: ChargeStatus;

  @ApiPropertyOptional()
  @IsOptional()
  @IsString()
  @ValidateBy({ name: 'maxLength', validator: { validate: (value: unknown): boolean => typeof value === 'string' && Array.from(value).length <= 200, defaultMessage: (): string => '$property must be at most 200 characters long' } })
  declineReason!: string | null;


}
