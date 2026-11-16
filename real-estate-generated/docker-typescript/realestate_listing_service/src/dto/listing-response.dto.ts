import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import { PropertyKind } from '../enums/property-kind.enum';
import { ListingStatus } from '../enums/listing-status.enum';

export class ListingResponseDto {
  @ApiProperty()
  createdAt!: Date;
  @ApiProperty()
  updatedAt!: Date;
  @ApiProperty()
  id!: string;
  @ApiProperty()
  title!: string;
  @ApiProperty()
  neighbourhoodName!: string;
  @ApiProperty()
  kind!: PropertyKind;
  @ApiProperty()
  price!: DecimalString;
  @ApiProperty()
  bedrooms!: number;
  @ApiProperty()
  bathrooms!: number;
  @ApiProperty()
  areaSqm!: number;
  @ApiProperty()
  status!: ListingStatus;
  @ApiProperty()
  agentName!: string;
  @ApiPropertyOptional()
  publishedAt?: Date | null;
  @ApiProperty()
  summary!: string;
  @ApiProperty()
  city!: string;
  @ApiProperty()
  latitude!: number;
  @ApiProperty()
  longitude!: number;
  @ApiProperty()
  agentEmail!: string;

}
