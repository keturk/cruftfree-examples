import { ApiProperty, ApiPropertyOptional, ApiSchema } from '@nestjs/swagger';

@ApiSchema({ description: 'API keys the vendor issued. Only the SHA-256 hash of a key is stored.' })
export class ApiKeyResponseDto {
  @ApiProperty()
  createdAt!: Date;
  @ApiProperty()
  updatedAt!: Date;
  @ApiProperty()
  id!: string;
  @ApiProperty()
  keyHash!: string;
  @ApiProperty()
  ownerId!: string;
  @ApiProperty()
  scopes!: string[];
  @ApiProperty()
  isActive!: boolean;
  @ApiPropertyOptional()
  expiresAt?: Date | null;
  @ApiPropertyOptional()
  lastUsedAt?: Date | null;

}
