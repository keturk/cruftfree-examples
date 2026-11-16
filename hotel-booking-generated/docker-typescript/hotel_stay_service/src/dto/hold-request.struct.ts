import {
  IsDate,
  IsInt,
  Matches,
  MaxLength,
  MinLength,
} from 'class-validator';
import { ApiProperty } from '@nestjs/swagger';
import { Type } from 'class-transformer';

export class HoldRequest {

  @ApiProperty({ format: 'uuid' })
  @MinLength(36)
  @MaxLength(36)
  @Matches(new RegExp("^(?:[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12})$", "u"))
  roomTypeId!: string;

  @ApiProperty()
  @IsDate()
  @Type(() => Date)
  arrival!: string;

  @ApiProperty()
  @IsDate()
  @Type(() => Date)
  departure!: string;

  @ApiProperty()
  @IsInt()
  guests!: number;


}
