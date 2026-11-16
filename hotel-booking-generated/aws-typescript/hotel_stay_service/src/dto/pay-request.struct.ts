import {
  IsEnum,
  Matches,
  MaxLength,
  MinLength,
} from 'class-validator';
import { ApiProperty } from '@nestjs/swagger';
import { TestCard } from '../enums/test-card.enum'

export class PayRequest {

  @ApiProperty({ format: 'uuid' })
  @MinLength(36)
  @MaxLength(36)
  @Matches(new RegExp("^(?:[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12})$", "u"))
  stayId!: string;

  @ApiProperty({ enum: TestCard, enumName: 'TestCard', enumSchema: { description: 'Stands in for the card form a real vendor would host. The application never sees a card number: it only\n\never holds the vendor\'s token, and these two choose which token the mock receives.' } })
  @IsEnum(TestCard)
  card!: TestCard;


}
