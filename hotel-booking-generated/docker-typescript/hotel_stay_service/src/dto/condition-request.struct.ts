import {
  IsEnum,
} from 'class-validator';
import { ApiProperty } from '@nestjs/swagger';
import { RoomCondition } from '../enums/room-condition.enum'

export class ConditionRequest {

  @ApiProperty({ enum: RoomCondition, enumName: 'RoomCondition', enumSchema: { description: 'The housekeeping board\'s columns.' } })
  @IsEnum(RoomCondition)
  condition!: RoomCondition;


}
