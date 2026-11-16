import { ApiProperty, ApiPropertyOptional, ApiSchema } from '@nestjs/swagger';

@ApiSchema({ description: 'What a guest chooses.' })
export class RoomTypeResponseDto {
  @ApiProperty()
  createdAt!: Date;
  @ApiProperty()
  updatedAt!: Date;
  @ApiProperty()
  id!: string;
  @ApiProperty()
  name!: string;
  @ApiProperty()
  summary!: string;
  @ApiProperty()
  description!: string;
  @ApiProperty()
  sleeps!: number;
  @ApiProperty()
  nightlyRate!: DecimalString;
  @ApiProperty()
  inventory!: number;
  @ApiProperty()
  listed!: boolean;

}
