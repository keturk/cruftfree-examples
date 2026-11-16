import {
  IsNotEmpty,
  IsObject,
  IsOptional,
  IsString,
  ValidateNested,
} from 'class-validator';
import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import { Type } from 'class-transformer';
import { StayCard } from '../dto/stay-card.struct'

export class DeskStay {

  @ApiProperty({ type: () => StayCard })
  @IsObject()
  @ValidateNested()
  @Type(() => StayCard)
  stay!: StayCard;

  @ApiProperty()
  @IsString()
  @IsNotEmpty()
  guestEmail!: string;

  @ApiPropertyOptional()
  @IsOptional()
  @IsString()
  deskNote!: string | null;


}
