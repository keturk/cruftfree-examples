import {
  IsDate,
  IsInt,
} from 'class-validator';
import { ApiProperty } from '@nestjs/swagger';
import { Type } from 'class-transformer';

export class SearchRequest {

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
