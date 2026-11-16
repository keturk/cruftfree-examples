import {
  IsEnum,
  IsNotEmpty,
  IsString,
  ValidateBy,
} from 'class-validator';
import { ApiProperty } from '@nestjs/swagger';
import { PreapprovalDecision } from '../enums/preapproval-decision.enum'

export class Preapproval {

  @ApiProperty()
  @IsString()
  @IsNotEmpty()
  @ValidateBy({ name: 'maxLength', validator: { validate: (value: unknown): boolean => typeof value === 'string' && Array.from(value).length <= 40, defaultMessage: (): string => '$property must be at most 40 characters long' } })
  reference!: string;

  @ApiProperty({ enum: PreapprovalDecision, enumName: 'PreapprovalDecision' })
  @IsEnum(PreapprovalDecision)
  decision!: PreapprovalDecision;


}
