import {
  Entity,
  Property,
  Check,
  OptionalProps,
} from '@mikro-orm/core';


import { BaseEntity } from './base-entity.entity';

@Check({ name: "ck_room_types_name_max_length", expression: "(char_length(\"name\") \u003c= 80)" })
@Check({ name: "ck_room_types_summary_max_length", expression: "(char_length(\"summary\") \u003c= 200)" })
@Entity({ tableName: 'room_types' })
export class RoomType extends BaseEntity {
  [OptionalProps]?: "createdAt" | "id" | "listed" | "updatedAt";


  @Property({ columnType: 'varchar', unique: true, length: 80 })
  name!: string;

  @Property({ columnType: 'varchar', length: 200 })
  summary!: string;

  @Property({ columnType: 'text' })
  description!: string;

  @Property({ columnType: 'int' })
  sleeps!: number;

  @Property({ columnType: 'decimal', fieldName: 'nightly_rate' })
  nightlyRate!: DecimalString;

  @Property({ columnType: 'int' })
  inventory!: number;

  @Property({ columnType: 'boolean', default: true })
  listed: boolean = true;





}
