import {
  IsArray,
  IsInt,
  ValidateNested,
} from 'class-validator';
import { ApiProperty } from '@nestjs/swagger';
import { Type } from 'class-transformer';
import { DayLoad } from '../dto/day-load.struct'

export class ViewingSummary {

  @ApiProperty()
  @IsInt()
  waitingForYou!: number;

  @ApiProperty()
  @IsInt()
  nextSevenDays!: number;

  @ApiProperty({ type: () => DayLoad, isArray: true })
  @IsArray()
  @ValidateNested({ each: true })
  @Type(() => DayLoad)
  ahead!: DayLoad[];


}
