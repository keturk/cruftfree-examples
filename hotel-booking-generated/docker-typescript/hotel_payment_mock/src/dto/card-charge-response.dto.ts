import { ApiProperty, ApiPropertyOptional, ApiSchema } from '@nestjs/swagger';
import { ChargeStatus } from '../enums/charge-status.enum';

@ApiSchema({ description: 'A charge the vendor answered.' })
export class CardChargeResponseDto {
  @ApiProperty()
  createdAt!: Date;
  @ApiProperty()
  updatedAt!: Date;
  @ApiProperty()
  id!: string;
  @ApiProperty()
  reference!: string;
  @ApiProperty()
  amount!: DecimalString;
  @ApiProperty()
  currency!: string;
  @ApiProperty()
  status!: ChargeStatus;
  @ApiPropertyOptional()
  declineReason?: string | null;
  @ApiProperty()
  chargeId!: string;
  @ApiProperty()
  idempotencyKey!: string;

}
