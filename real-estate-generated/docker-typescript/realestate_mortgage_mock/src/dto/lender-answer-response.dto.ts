import { ApiProperty, ApiPropertyOptional, ApiSchema } from '@nestjs/swagger';
import { PreapprovalDecision } from '../enums/preapproval-decision.enum';

@ApiSchema({ description: 'An answer the lender gave.' })
export class LenderAnswerResponseDto {
  @ApiProperty()
  createdAt!: Date;
  @ApiProperty()
  updatedAt!: Date;
  @ApiProperty()
  id!: string;
  @ApiProperty()
  applicantName!: string;
  @ApiProperty()
  amount!: DecimalString;
  @ApiProperty()
  decision!: PreapprovalDecision;
  @ApiProperty()
  reference!: string;
  @ApiProperty()
  idempotencyKey!: string;
  @ApiProperty()
  applicantEmail!: string;

}
