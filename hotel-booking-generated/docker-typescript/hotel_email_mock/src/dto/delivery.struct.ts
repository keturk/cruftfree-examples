import {
  IsEnum,
  IsNotEmpty,
  IsString,
  ValidateBy,
} from 'class-validator';
import { ApiProperty } from '@nestjs/swagger';
import { DeliveryStatus } from '../enums/delivery-status.enum'

export class Delivery {

  @ApiProperty()
  @IsString()
  @IsNotEmpty()
  @ValidateBy({ name: 'maxLength', validator: { validate: (value: unknown): boolean => typeof value === 'string' && Array.from(value).length <= 40, defaultMessage: (): string => '$property must be at most 40 characters long' } })
  id!: string;

  @ApiProperty({ enum: DeliveryStatus, enumName: 'DeliveryStatus' })
  @IsEnum(DeliveryStatus)
  status!: DeliveryStatus;


}
