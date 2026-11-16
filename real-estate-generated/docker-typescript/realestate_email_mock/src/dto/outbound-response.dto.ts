import { ApiProperty, ApiPropertyOptional, ApiSchema } from '@nestjs/swagger';
import { DeliveryStatus } from '../enums/delivery-status.enum';

@ApiSchema({ description: 'An email the vendor accepted.' })
export class OutboundResponseDto {
  @ApiProperty()
  createdAt!: Date;
  @ApiProperty()
  updatedAt!: Date;
  @ApiProperty()
  id!: string;
  @ApiProperty()
  recipient!: string;
  @ApiProperty()
  subject!: string;
  @ApiProperty()
  body!: string;
  @ApiProperty()
  status!: DeliveryStatus;
  @ApiProperty()
  deliveryId!: string;
  @ApiProperty()
  idempotencyKey!: string;

}
