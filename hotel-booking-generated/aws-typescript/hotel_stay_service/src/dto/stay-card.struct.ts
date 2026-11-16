import {
  IsBoolean,
  IsDate,
  IsEnum,
  IsInt,
  IsNotEmpty,
  IsOptional,
  IsString,
  Matches,
  MaxLength,
  MinLength,
} from 'class-validator';
import { ApiProperty, ApiPropertyOptional, ApiSchema } from '@nestjs/swagger';
import { Transform, Type } from 'class-transformer';
import { StayStatus } from '../enums/stay-status.enum'

@ApiSchema({ description: 'A stay as a guest sees it. There is no field here for the desk\'s note.' })
export class StayCard {

  @ApiProperty({ format: 'uuid' })
  @MinLength(36)
  @MaxLength(36)
  @Matches(new RegExp("^(?:[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12})$", "u"))
  id!: string;

  @ApiProperty()
  @IsString()
  @IsNotEmpty()
  code!: string;

  @ApiProperty()
  @IsString()
  @IsNotEmpty()
  roomTypeName!: string;

  @ApiPropertyOptional()
  @IsOptional()
  @IsString()
  roomNumber!: string | null;

  @ApiProperty()
  @IsString()
  @IsNotEmpty()
  guestName!: string;

  @ApiProperty()
  @IsDate()
  @Type(() => Date)
  arrival!: string;

  @ApiProperty()
  @IsDate()
  @Type(() => Date)
  departure!: string;

  @ApiProperty()
  @IsInt()
  nights!: number;

  @ApiProperty()
  @IsInt()
  guests!: number;

  @ApiProperty()
  @Transform(({ value }) => (typeof value === 'number' ? String(value) : value))
  @Matches(/^[+-]?([0-9]+(\.[0-9]*)?|\.[0-9]+)([eE][+-]?[0-9]+)?$/, { message: '$property must be a decimal number' })
  total!: DecimalString;

  @ApiProperty({ enum: StayStatus, enumName: 'StayStatus', enumSchema: { description: 'A stay from the first hold to the last goodbye.' } })
  @IsEnum(StayStatus)
  status!: StayStatus;

  @ApiProperty({ description: 'When a held stay lapses. For any other stay, when it was made: only a hold shows it.' })
  @IsDate()
  @Type(() => Date)
  holdEnds!: Date;

  @ApiProperty()
  @IsBoolean()
  canCancel!: boolean;


}
