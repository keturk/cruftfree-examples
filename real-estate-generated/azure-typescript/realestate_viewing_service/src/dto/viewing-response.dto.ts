import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import { ViewingStatus } from '../enums/viewing-status.enum';

export class ViewingResponseDto {
  @ApiProperty()
  createdAt!: Date;
  @ApiProperty()
  updatedAt!: Date;
  @ApiProperty()
  id!: string;
  @ApiProperty()
  startsAt!: Date;
  @ApiProperty()
  endsAt!: Date;
  @ApiProperty()
  listingTitle!: string;
  @ApiProperty()
  buyerName!: string;
  @ApiProperty()
  status!: ViewingStatus;
  @ApiProperty()
  agentName!: string;
  @ApiPropertyOptional()
  note?: string | null;
  @ApiProperty()
  listingId!: string;
  @ApiProperty()
  buyerEmail!: string;
  @ApiProperty()
  agentEmail!: string;
  @ApiProperty()
  reminderSent!: boolean;

}
