import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import { ContractStatus } from '../enums/contract-status.enum';

export class ContractResponseDto {
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
  price!: DecimalString;
  @ApiProperty()
  status!: ContractStatus;
  @ApiPropertyOptional()
  signedAt?: Date | null;
  @ApiPropertyOptional()
  envelopeId?: string | null;
  @ApiProperty()
  listingId!: string;
  @ApiProperty()
  offerId!: string;
  @ApiProperty()
  buyerEmail!: string;
  @ApiProperty()
  agentEmail!: string;

}
