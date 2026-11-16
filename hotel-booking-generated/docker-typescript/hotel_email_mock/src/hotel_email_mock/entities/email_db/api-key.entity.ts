import {
  Entity,
  Property,
  Index,
  Check,
  OptionalProps,
} from '@mikro-orm/core';


import { BaseEntity } from './base-entity.entity';

@Index({ name: 'ix_api_keys_owner_id', properties: ['ownerId'] })
@Check({ name: "ck_api_keys_key_hash_max_length", expression: "(char_length(\"key_hash\") \u003c= 64)" })
@Entity({ tableName: 'api_keys' })
export class ApiKey extends BaseEntity {
  [OptionalProps]?: "createdAt" | "expiresAt" | "id" | "isActive" | "lastUsedAt" | "scopes" | "updatedAt";


  @Property({ columnType: 'varchar', fieldName: 'key_hash', unique: true, length: 64 })
  keyHash!: string;

  @Property({ columnType: 'uuid', fieldName: 'owner_id' })
  ownerId!: string;

  @Property({ columnType: 'jsonb', type: 'json', default: [] })
  scopes: string[] = [];

  @Property({ columnType: 'boolean', fieldName: 'is_active', default: true })
  isActive: boolean = true;

  @Property({ columnType: 'timestamptz', fieldName: 'expires_at', nullable: true })
  expiresAt!: Date | null;

  @Property({ columnType: 'timestamptz', fieldName: 'last_used_at', nullable: true })
  lastUsedAt!: Date | null;





}
