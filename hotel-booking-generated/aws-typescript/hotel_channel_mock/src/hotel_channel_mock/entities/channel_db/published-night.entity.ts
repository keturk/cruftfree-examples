import {
  Entity,
  Property,
  Unique,
  Check,
  OptionalProps,
} from '@mikro-orm/core';


import { BaseEntity } from './base-entity.entity';

@Unique({ name: 'uq_published_nights_room_type_night', properties: ['roomType', 'night'] })
@Check({ name: "ck_published_nights_room_type_max_length", expression: "(char_length(\"room_type\") \u003c= 80)" })
@Entity({ tableName: 'published_nights' })
export class PublishedNight extends BaseEntity {
  [OptionalProps]?: "createdAt" | "id" | "updatedAt";


  @Property({ columnType: 'varchar', fieldName: 'room_type', length: 80 })
  roomType!: string;

  @Property({ columnType: 'date' })
  night!: string;

  @Property({ columnType: 'int' })
  left!: number;

  @Property({ columnType: 'decimal', fieldName: 'nightly_rate' })
  nightlyRate!: DecimalString;

  @Property({ columnType: 'timestamptz', fieldName: 'received_at' })
  receivedAt!: Date;





}
