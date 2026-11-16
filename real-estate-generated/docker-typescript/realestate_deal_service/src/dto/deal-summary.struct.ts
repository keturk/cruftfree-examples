import {
  IsInt,
  Matches,
} from 'class-validator';
import { ApiProperty } from '@nestjs/swagger';
import { Transform } from 'class-transformer';

export class DealSummary {

  @ApiProperty()
  @IsInt()
  offersWaiting!: number;

  @ApiProperty()
  @IsInt()
  contractsOut!: number;

  @ApiProperty()
  @IsInt()
  signed!: number;

  @ApiProperty()
  @Transform(({ value }) => (typeof value === 'number' ? String(value) : value))
  @Matches(/^[+-]?([0-9]+(\.[0-9]*)?|\.[0-9]+)([eE][+-]?[0-9]+)?$/, { message: '$property must be a decimal number' })
  signedValue!: DecimalString;


}
