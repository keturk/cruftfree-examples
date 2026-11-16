
import {
  IsDefined,
  IsNotEmpty,
  IsNumber,
  IsOptional,
  IsString,
  ValidateBy,
} from 'class-validator';
import { ApiProperty, ApiSchema } from '@nestjs/swagger';
import { Type } from 'class-transformer';

@ApiSchema({ description: 'A neighbourhood the agency works in. Choosing one places a home on the map.' })
export class CreateNeighbourhoodDto {

  @ApiProperty()
  @IsDefined()
  @IsString()
  @IsNotEmpty()
  @ValidateBy({ name: 'maxLength', validator: { validate: (value: unknown): boolean => typeof value === 'string' && Array.from(value).length <= 120, defaultMessage: (): string => '$property must be at most 120 characters long' } })
  name!: string;

  @ApiProperty()
  @IsDefined()
  @IsString()
  @IsNotEmpty()
  @ValidateBy({ name: 'maxLength', validator: { validate: (value: unknown): boolean => typeof value === 'string' && Array.from(value).length <= 120, defaultMessage: (): string => '$property must be at most 120 characters long' } })
  city!: string;

  @ApiProperty()
  @IsDefined()
  @IsNumber()
  latitude!: number;

  @ApiProperty()
  @IsDefined()
  @IsNumber()
  longitude!: number;
}
