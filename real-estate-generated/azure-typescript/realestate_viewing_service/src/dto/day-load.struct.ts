import {
  IsInt,
  IsNotEmpty,
  IsString,
} from 'class-validator';
import { ApiProperty } from '@nestjs/swagger';

export class DayLoad {

  @ApiProperty()
  @IsString()
  @IsNotEmpty()
  day!: string;

  @ApiProperty()
  @IsInt()
  viewings!: number;


}
