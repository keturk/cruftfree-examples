import {
  IsEnum,
  Matches,
  MaxLength,
  MinLength,
} from 'class-validator';
import { ApiProperty } from '@nestjs/swagger';
import { Transform } from 'class-transformer';
import { Financing } from '../enums/financing.enum'

export class MakeOffer {

  @ApiProperty({ format: 'uuid' })
  @MinLength(36)
  @MaxLength(36)
  @Matches(new RegExp("^(?:[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12})$", "u"))
  listingId!: string;

  @ApiProperty()
  @Transform(({ value }) => (typeof value === 'number' ? String(value) : value))
  @Matches(/^[+-]?([0-9]+(\.[0-9]*)?|\.[0-9]+)([eE][+-]?[0-9]+)?$/, { message: '$property must be a decimal number' })
  amount!: DecimalString;

  @ApiProperty({ enum: Financing, enumName: 'Financing' })
  @IsEnum(Financing)
  financing!: Financing;


}
