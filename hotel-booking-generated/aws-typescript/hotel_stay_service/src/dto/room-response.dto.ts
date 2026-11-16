import { ApiProperty, ApiPropertyOptional, ApiSchema } from '@nestjs/swagger';
import { RoomCondition } from '../enums/room-condition.enum';

@ApiSchema({ description: 'A door with a number. Only the desk thinks about these.' })
export class RoomResponseDto {
  @ApiProperty()
  createdAt!: Date;
  @ApiProperty()
  updatedAt!: Date;
  @ApiProperty()
  id!: string;
  @ApiProperty()
  number!: string;
  @ApiProperty()
  roomTypeId!: string;
  @ApiProperty()
  roomTypeName!: string;
  @ApiProperty()
  floor!: number;
  @ApiProperty()
  condition!: RoomCondition;

}
