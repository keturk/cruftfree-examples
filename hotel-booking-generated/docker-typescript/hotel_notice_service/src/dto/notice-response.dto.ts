import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';

export class NoticeResponseDto {
  @ApiProperty()
  createdAt!: Date;
  @ApiProperty()
  updatedAt!: Date;
  @ApiProperty()
  id!: string;
  @ApiProperty()
  recipient!: string;
  @ApiProperty()
  subject!: string;
  @ApiProperty()
  body!: string;
  @ApiProperty()
  delivered!: boolean;
  @ApiProperty()
  attempts!: number;
  @ApiProperty()
  noticeKey!: string;

}
