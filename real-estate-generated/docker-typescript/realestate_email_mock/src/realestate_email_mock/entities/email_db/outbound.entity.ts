import {
  Entity,
  Property,
  Enum,
  Check,
  OptionalProps,
} from '@mikro-orm/core';


import { DeliveryStatus, DeliveryStatusStorage } from '../../../enums/delivery-status.enum';
import { BaseEntity } from './base-entity.entity';

@Check({ name: "ck_outbounds_recipient_max_length", expression: "(char_length(\"recipient\") \u003c= 200)" })
@Check({ name: "ck_outbounds_subject_max_length", expression: "(char_length(\"subject\") \u003c= 200)" })
@Check({ name: "ck_outbounds_body_max_length", expression: "(char_length(\"body\") \u003c= 2000)" })
@Check({ name: "ck_outbounds_delivery_id_max_length", expression: "(char_length(\"delivery_id\") \u003c= 40)" })
@Check({ name: "ck_outbounds_idempotency_key_max_length", expression: "(char_length(\"idempotency_key\") \u003c= 120)" })
@Entity({ tableName: 'outbounds' })
export class Outbound extends BaseEntity {
  [OptionalProps]?: "createdAt" | "id" | "updatedAt";


  @Property({ columnType: 'varchar', length: 200 })
  recipient!: string;

  @Property({ columnType: 'varchar', length: 200 })
  subject!: string;

  @Property({ columnType: 'varchar', length: 2000 })
  body!: string;

  @Enum({ items: DeliveryStatusStorage.labels, nativeEnumName: 'delivery_status', type: DeliveryStatusStorage })
  status!: DeliveryStatus;

  @Property({ columnType: 'varchar', fieldName: 'delivery_id', unique: true, length: 40 })
  deliveryId!: string;

  @Property({ columnType: 'varchar', fieldName: 'idempotency_key', unique: true, length: 120 })
  idempotencyKey!: string;





}
