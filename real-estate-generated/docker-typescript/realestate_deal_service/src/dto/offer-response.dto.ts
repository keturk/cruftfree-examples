import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import { Financing } from '../enums/financing.enum';
import { OfferStatus } from '../enums/offer-status.enum';

export class OfferResponseDto {
  @ApiProperty()
  createdAt!: Date;
  @ApiProperty()
  updatedAt!: Date;
  @ApiProperty()
  id!: string;
  @ApiProperty()
  listingTitle!: string;
  @ApiProperty()
  buyerName!: string;
  @ApiProperty()
  amount!: DecimalString;
  @ApiProperty()
  financing!: Financing;
  @ApiProperty()
  status!: OfferStatus;
  @ApiPropertyOptional()
  lenderReference?: string | null;
  @ApiProperty()
  listingId!: string;
  @ApiProperty()
  buyerEmail!: string;
  @ApiProperty()
  agentEmail!: string;

}
