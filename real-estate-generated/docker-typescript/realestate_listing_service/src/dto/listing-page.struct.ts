import {
  IsArray,
  IsNotEmpty,
  IsObject,
  IsString,
  ValidateNested,
} from 'class-validator';
import { ApiProperty } from '@nestjs/swagger';
import { Type } from 'class-transformer';
import { GeoPoint } from '../dto/geo-point.struct'
import { ListingCard } from '../dto/listing-card.struct'
import { PriceStep } from '../dto/price-step.struct'

export class ListingPage {

  @ApiProperty({ type: () => ListingCard })
  @IsObject()
  @ValidateNested()
  @Type(() => ListingCard)
  home!: ListingCard;

  @ApiProperty()
  @IsString()
  @IsNotEmpty()
  summary!: string;

  @ApiProperty()
  @IsString()
  @IsNotEmpty()
  agentName!: string;

  @ApiProperty({ type: () => GeoPoint })
  @IsObject()
  @ValidateNested()
  @Type(() => GeoPoint)
  point!: GeoPoint;

  @ApiProperty({ type: () => PriceStep, isArray: true })
  @IsArray()
  @ValidateNested({ each: true })
  @Type(() => PriceStep)
  priceHistory!: PriceStep[];


}
