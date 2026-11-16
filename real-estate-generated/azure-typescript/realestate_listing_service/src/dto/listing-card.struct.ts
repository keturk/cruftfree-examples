import {
  IsEnum,
  IsInt,
  IsNotEmpty,
  IsString,
  Matches,
  MaxLength,
  MinLength,
} from 'class-validator';
import { ApiProperty, ApiSchema } from '@nestjs/swagger';
import { Transform } from 'class-transformer';
import { ListingStatus } from '../enums/listing-status.enum'
import { PropertyKind } from '../enums/property-kind.enum'

@ApiSchema({ description: 'A home in a search. The agent\'s address stays on the server.' })
export class ListingCard {

  @ApiProperty({ format: 'uuid' })
  @MinLength(36)
  @MaxLength(36)
  @Matches(new RegExp("^(?:[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12})$", "u"))
  id!: string;

  @ApiProperty()
  @IsString()
  @IsNotEmpty()
  title!: string;

  @ApiProperty()
  @IsString()
  @IsNotEmpty()
  neighbourhoodName!: string;

  @ApiProperty()
  @IsString()
  @IsNotEmpty()
  city!: string;

  @ApiProperty({ enum: PropertyKind, enumName: 'PropertyKind' })
  @IsEnum(PropertyKind)
  kind!: PropertyKind;

  @ApiProperty()
  @Transform(({ value }) => (typeof value === 'number' ? String(value) : value))
  @Matches(/^[+-]?([0-9]+(\.[0-9]*)?|\.[0-9]+)([eE][+-]?[0-9]+)?$/, { message: '$property must be a decimal number' })
  price!: DecimalString;

  @ApiProperty()
  @IsInt()
  bedrooms!: number;

  @ApiProperty()
  @IsInt()
  bathrooms!: number;

  @ApiProperty()
  @IsInt()
  areaSqm!: number;

  @ApiProperty({ enum: ListingStatus, enumName: 'ListingStatus', enumSchema: { description: 'Where a home is in being sold. An offer and a viewing are only taken while it is Active.' } })
  @IsEnum(ListingStatus)
  status!: ListingStatus;


}
