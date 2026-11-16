import {
  IsDate,
  IsNotEmpty,
  IsString,
  Matches,
  MaxLength,
  MinLength,
} from 'class-validator';
import { ApiProperty, ApiSchema } from '@nestjs/swagger';
import { Type } from 'class-transformer';

@ApiSchema({ description: 'A stay on the desk\'s calendar, whose bars run from noon on arrival to noon on departure.' })
export class CalendarStay {

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
  @IsDate()
  @Type(() => Date)
  startsAt!: Date;

  @ApiProperty()
  @IsDate()
  @Type(() => Date)
  endsAt!: Date;


}
