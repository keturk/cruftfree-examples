import {
  IsArray,
  IsNotEmpty,
  IsString,
  ValidateBy,
  ValidateNested,
} from 'class-validator';
import { ApiProperty } from '@nestjs/swagger';
import { Type } from 'class-transformer';
import { AvailabilityUpdate } from '../dto/availability-update.struct'

export class AvailabilityPush {

  @ApiProperty()
  @IsString()
  @IsNotEmpty()
  @ValidateBy({ name: 'maxLength', validator: { validate: (value: unknown): boolean => typeof value === 'string' && Array.from(value).length <= 40, defaultMessage: (): string => '$property must be at most 40 characters long' } })
  propertyCode!: string;

  @ApiProperty({ type: () => AvailabilityUpdate, isArray: true })
  @IsArray()
  @ValidateNested({ each: true })
  @Type(() => AvailabilityUpdate)
  nights!: AvailabilityUpdate[];


}
