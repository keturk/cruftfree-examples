import { ApiProperty, ApiPropertyOptional, ApiSchema } from '@nestjs/swagger';
import { EnvelopeStatus } from '../enums/envelope-status.enum';

@ApiSchema({ description: 'A document waiting for a signature.' })
export class VendorEnvelopeResponseDto {
  @ApiProperty()
  createdAt!: Date;
  @ApiProperty()
  updatedAt!: Date;
  @ApiProperty()
  id!: string;
  @ApiProperty()
  signerName!: string;
  @ApiProperty()
  documentTitle!: string;
  @ApiProperty()
  status!: EnvelopeStatus;
  @ApiPropertyOptional()
  settledAt?: Date | null;
  @ApiProperty()
  documentBody!: string;
  @ApiProperty()
  signerEmail!: string;
  @ApiProperty()
  envelopeId!: string;
  @ApiProperty()
  idempotencyKey!: string;

}
