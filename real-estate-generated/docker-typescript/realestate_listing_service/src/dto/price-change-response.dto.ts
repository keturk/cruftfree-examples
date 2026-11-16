import { ApiProperty, ApiPropertyOptional, ApiSchema } from '@nestjs/swagger';

@ApiSchema({ description: 'Every price a home has asked. Never changed once written.' })
export class PriceChangeResponseDto {
  @ApiProperty()
  createdAt!: Date;
  @ApiProperty()
  updatedAt!: Date;
  @ApiProperty()
  id!: string;
  @ApiProperty()
  listingId!: string;
  @ApiProperty()
  oldPrice!: DecimalString;
  @ApiProperty()
  newPrice!: DecimalString;

}
