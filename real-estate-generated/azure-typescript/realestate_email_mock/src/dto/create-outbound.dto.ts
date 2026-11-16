
import {
  IsDefined,
  IsEnum,
  IsNotEmpty,
  IsOptional,
  IsString,
  ValidateBy,
} from 'class-validator';
import { ApiProperty, ApiSchema } from '@nestjs/swagger';
import { Type } from 'class-transformer';
import { DeliveryStatus } from '../enums/delivery-status.enum';

@ApiSchema({ description: 'An email the vendor accepted.' })
export class CreateOutboundDto {

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

  @ApiProperty({ enum: DeliveryStatus, enumName: 'DeliveryStatus' })
  @IsDefined()
  @IsEnum(DeliveryStatus)
  status!: DeliveryStatus;

  @ApiProperty()
  @IsDefined()
  @IsString()
  @IsNotEmpty()
  @ValidateBy({ name: 'maxLength', validator: { validate: (value: unknown): boolean => typeof value === 'string' && Array.from(value).length <= 40, defaultMessage: (): string => '$property must be at most 40 characters long' } })
  deliveryId!: string;

  @ApiProperty()
  @IsDefined()
  @IsString()
  @IsNotEmpty()
  @ValidateBy({ name: 'maxLength', validator: { validate: (value: unknown): boolean => typeof value === 'string' && Array.from(value).length <= 120, defaultMessage: (): string => '$property must be at most 120 characters long' } })
  idempotencyKey!: string;
}
