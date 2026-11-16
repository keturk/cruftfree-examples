import {
  IsInt,
} from 'class-validator';
import { ApiProperty } from '@nestjs/swagger';

export class DeskSummary {

  @ApiProperty()
  @IsInt()
  arrivals!: number;

  @ApiProperty()
  @IsInt()
  departures!: number;

  @ApiProperty()
  @IsInt()
  inHouse!: number;

  @ApiProperty()
  @IsInt()
  roomsToClean!: number;

  @ApiProperty()
  @IsInt()
  occupancyPercent!: number;


}
