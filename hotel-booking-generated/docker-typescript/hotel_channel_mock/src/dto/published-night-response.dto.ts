import { ApiProperty, ApiPropertyOptional, ApiSchema } from '@nestjs/swagger';

@ApiSchema({ description: 'What the travel sites currently believe about one room type on one night.' })
export class PublishedNightResponseDto {
  @ApiProperty()
  createdAt!: Date;
  @ApiProperty()
  updatedAt!: Date;
  @ApiProperty()
  id!: string;
  @ApiProperty()
  roomType!: string;
  @ApiProperty()
  night!: string;
  @ApiProperty()
  left!: number;
  @ApiProperty()
  nightlyRate!: DecimalString;
  @ApiProperty()
  receivedAt!: Date;

}
