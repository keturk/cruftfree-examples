import {
  Entity,
  Property,
  Enum,
  Index,
  Check,
  OptionalProps,
} from '@mikro-orm/core';


import { StayStatus, StayStatusStorage } from '../../../enums/stay-status.enum';
import { BaseEntity } from './base-entity.entity';

@Index({ name: 'ix_stays_room_type_id', properties: ['roomTypeId'] })
@Index({ name: 'ix_stays_guest_id', properties: ['guestId'] })
@Index({ name: 'ix_stays_room_type_id_arrival_departure', properties: ['roomTypeId', 'arrival', 'departure'] })
@Index({ name: 'ix_stays_status_hold_until', properties: ['status', 'holdUntil'] })
@Check({ name: "ck_stays_code_max_length", expression: "(char_length(\"code\") \u003c= 20)" })
@Check({ name: "ck_stays_room_type_name_max_length", expression: "(char_length(\"room_type_name\") \u003c= 80)" })
@Check({ name: "ck_stays_room_number_max_length", expression: "(char_length(\"room_number\") \u003c= 8)" })
@Check({ name: "ck_stays_guest_id_max_length", expression: "(char_length(\"guest_id\") \u003c= 64)" })
@Check({ name: "ck_stays_guest_name_max_length", expression: "(char_length(\"guest_name\") \u003c= 200)" })
@Check({ name: "ck_stays_charge_id_max_length", expression: "(char_length(\"charge_id\") \u003c= 40)" })
@Entity({ tableName: 'stays' })
export class Stay extends BaseEntity {
  [OptionalProps]?: "chargeId" | "createdAt" | "deskNote" | "holdUntil" | "id" | "roomNumber" | "status" | "updatedAt";


  @Property({ columnType: 'varchar', unique: true, length: 20 })
  code!: string;

  @Property({ columnType: 'uuid', fieldName: 'room_type_id' })
  roomTypeId!: string;

  @Property({ columnType: 'varchar', fieldName: 'room_type_name', length: 80 })
  roomTypeName!: string;

  @Property({ columnType: 'varchar', fieldName: 'room_number', nullable: true, length: 8 })
  roomNumber!: string | null;

  @Property({ columnType: 'varchar', fieldName: 'guest_id', length: 64 })
  guestId!: string;

  @Property({ columnType: 'varchar', fieldName: 'guest_name', length: 200 })
  guestName!: string;

  @Property({ columnType: 'varchar', fieldName: 'guest_email' })
  guestEmail!: string;

  @Property({ columnType: 'date' })
  arrival!: string;

  @Property({ columnType: 'date' })
  departure!: string;

  @Property({ columnType: 'int' })
  nights!: number;

  @Property({ columnType: 'int' })
  guests!: number;

  @Property({ columnType: 'decimal' })
  total!: DecimalString;

  @Enum({ items: StayStatusStorage.labels, nativeEnumName: 'stay_status', type: StayStatusStorage })
  status: StayStatus = StayStatus.Held;

  @Property({ columnType: 'timestamptz', fieldName: 'hold_until', nullable: true })
  holdUntil!: Date | null;

  @Property({ columnType: 'varchar', fieldName: 'charge_id', nullable: true, length: 40 })
  chargeId!: string | null;

  @Property({ columnType: 'text', fieldName: 'desk_note', nullable: true })
  deskNote!: string | null;





}
