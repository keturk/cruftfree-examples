import {
  Entity,
  Property,
  Index,
  Check,
  OptionalProps,
} from '@mikro-orm/core';


import { BaseEntity } from './base-entity.entity';

@Index({ name: 'ix_notices_delivered', properties: ['delivered'] })
@Check({ name: "ck_notices_recipient_max_length", expression: "(char_length(\"recipient\") \u003c= 200)" })
@Check({ name: "ck_notices_subject_max_length", expression: "(char_length(\"subject\") \u003c= 200)" })
@Check({ name: "ck_notices_body_max_length", expression: "(char_length(\"body\") \u003c= 2000)" })
@Check({ name: "ck_notices_notice_key_max_length", expression: "(char_length(\"notice_key\") \u003c= 120)" })
@Entity({ tableName: 'notices' })
export class Notice extends BaseEntity {
  [OptionalProps]?: "attempts" | "createdAt" | "delivered" | "id" | "updatedAt";


  @Property({ columnType: 'varchar', length: 200 })
  recipient!: string;

  @Property({ columnType: 'varchar', length: 200 })
  subject!: string;

  @Property({ columnType: 'varchar', length: 2000 })
  body!: string;

  @Property({ columnType: 'boolean', default: false })
  delivered: boolean = false;

  @Property({ columnType: 'int', default: 0 })
  attempts: number = 0;

  @Property({ columnType: 'varchar', fieldName: 'notice_key', unique: true, length: 120 })
  noticeKey!: string;





}
