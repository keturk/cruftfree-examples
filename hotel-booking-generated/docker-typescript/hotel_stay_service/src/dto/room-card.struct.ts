import {
  IsEnum,
  IsInt,
  IsNotEmpty,
  IsString,
  Matches,
  MaxLength,
  MinLength,
} from 'class-validator';
import { ApiProperty } from '@nestjs/swagger';
import { RoomCondition } from '../enums/room-condition.enum'

export class RoomCard {

  @ApiProperty({ format: 'uuid' })
  @MinLength(36)
  @MaxLength(36)
  @Matches(new RegExp("^(?:[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12})$", "u"))
  id!: string;

  @ApiProperty()
  @IsString()
  @IsNotEmpty()
  number!: string;

  @ApiProperty()
  @IsString()
  @IsNotEmpty()
  roomTypeName!: string;

  @ApiProperty()
  @IsInt()
  floor!: number;

  @ApiProperty({ enum: RoomCondition, enumName: 'RoomCondition', enumSchema: { description: 'The housekeeping board\'s columns.' } })
  @IsEnum(RoomCondition)
  condition!: RoomCondition;


}
