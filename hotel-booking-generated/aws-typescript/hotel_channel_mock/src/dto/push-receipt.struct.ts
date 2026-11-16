import {
  IsInt,
} from 'class-validator';
import { ApiProperty } from '@nestjs/swagger';

export class PushReceipt {

  @ApiProperty()
  @IsInt()
  accepted!: number;


}
