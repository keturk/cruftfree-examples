import {
  IsInt,
} from 'class-validator';
import { ApiProperty } from '@nestjs/swagger';

export class PageRequest {

  @ApiProperty()
  @IsInt()
  offset!: number;

  @ApiProperty()
  @IsInt()
  limit!: number;


}
