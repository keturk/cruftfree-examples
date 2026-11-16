import {
  IsDate,
  IsOptional,
  IsString,
  Matches,
  MaxLength,
  MinLength,
  ValidateBy,
} from 'class-validator';
import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import { Type } from 'class-transformer';

export class RequestViewing {

  @ApiProperty({ format: 'uuid' })
  @MinLength(36)
  @MaxLength(36)
  @Matches(new RegExp("^(?:[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12})$", "u"))
  listingId!: string;

  @ApiProperty()
  @IsDate()
  @Type(() => Date)
  startsAt!: Date;

  @ApiPropertyOptional()
  @IsOptional()
  @IsString()
  @ValidateBy({ name: 'maxLength', validator: { validate: (value: unknown): boolean => typeof value === 'string' && Array.from(value).length <= 500, defaultMessage: (): string => '$property must be at most 500 characters long' } })
  note!: string | null;


}
