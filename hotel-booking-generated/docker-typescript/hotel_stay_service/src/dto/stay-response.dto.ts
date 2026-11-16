import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import { StayStatus } from '../enums/stay-status.enum';

export class StayResponseDto {
  @ApiProperty()
  createdAt!: Date;
  @ApiProperty()
  updatedAt!: Date;
  @ApiProperty()
  id!: string;
  @ApiProperty()
  code!: string;
  @ApiProperty()
  roomTypeId!: string;
  @ApiProperty()
  roomTypeName!: string;
  @ApiPropertyOptional()
  roomNumber?: string | null;
  @ApiProperty()
  guestId!: string;
  @ApiProperty()
  guestName!: string;
  @ApiProperty()
  guestEmail!: string;
  @ApiProperty()
  arrival!: string;
  @ApiProperty()
  departure!: string;
  @ApiProperty()
  nights!: number;
  @ApiProperty()
  guests!: number;
  @ApiProperty()
  total!: DecimalString;
  @ApiProperty()
  status!: StayStatus;
  @ApiPropertyOptional()
  holdUntil?: Date | null;
  @ApiPropertyOptional()
  chargeId?: string | null;
  @ApiPropertyOptional()
  deskNote?: string | null;

}
