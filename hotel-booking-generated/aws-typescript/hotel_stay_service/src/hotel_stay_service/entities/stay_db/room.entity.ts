import {
  Entity,
  Property,
  Enum,
  Index,
  Check,
  OptionalProps,
} from '@mikro-orm/core';


import { RoomCondition, RoomConditionStorage } from '../../../enums/room-condition.enum';
import { BaseEntity } from './base-entity.entity';

@Index({ name: 'ix_rooms_room_type_id', properties: ['roomTypeId'] })
@Check({ name: "ck_rooms_number_max_length", expression: "(char_length(\"number\") \u003c= 8)" })
@Check({ name: "ck_rooms_room_type_name_max_length", expression: "(char_length(\"room_type_name\") \u003c= 80)" })
@Entity({ tableName: 'rooms' })
export class Room extends BaseEntity {
  [OptionalProps]?: "condition" | "createdAt" | "id" | "updatedAt";


  @Property({ columnType: 'varchar', unique: true, length: 8 })
  number!: string;

  @Property({ columnType: 'uuid', fieldName: 'room_type_id' })
  roomTypeId!: string;

  @Property({ columnType: 'varchar', fieldName: 'room_type_name', length: 80 })
  roomTypeName!: string;

  @Property({ columnType: 'int' })
  floor!: number;

  @Enum({ items: RoomConditionStorage.labels, nativeEnumName: 'room_condition', type: RoomConditionStorage })
  condition: RoomCondition = RoomCondition.Ready;





}
