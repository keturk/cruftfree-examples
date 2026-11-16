import {
  IsInt,
  IsNotEmpty,
  IsString,
} from 'class-validator';
import { ApiProperty, ApiSchema } from '@nestjs/swagger';

@ApiSchema({ description: 'One night on the occupancy chart.' })
export class OccupancyPoint {

  @ApiProperty()
  @IsString()
  @IsNotEmpty()
  night!: string;

  @ApiProperty()
  @IsInt()
  sold!: number;

  @ApiProperty()
  @IsInt()
  left!: number;


}
