import {
  IsInt,
} from 'class-validator';
import { ApiProperty } from '@nestjs/swagger';

export class AgentSummary {

  @ApiProperty()
  @IsInt()
  onTheMarket!: number;

  @ApiProperty()
  @IsInt()
  drafts!: number;

  @ApiProperty()
  @IsInt()
  underOffer!: number;

  @ApiProperty()
  @IsInt()
  sold!: number;


}
