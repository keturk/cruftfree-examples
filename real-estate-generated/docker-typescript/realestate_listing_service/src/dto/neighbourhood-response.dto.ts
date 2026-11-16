import { ApiProperty, ApiPropertyOptional, ApiSchema } from '@nestjs/swagger';

@ApiSchema({ description: 'A neighbourhood the agency works in. Choosing one places a home on the map.' })
export class NeighbourhoodResponseDto {
  @ApiProperty()
  createdAt!: Date;
  @ApiProperty()
  updatedAt!: Date;
  @ApiProperty()
  id!: string;
  @ApiProperty()
  name!: string;
  @ApiProperty()
  city!: string;
  @ApiProperty()
  latitude!: number;
  @ApiProperty()
  longitude!: number;

}
