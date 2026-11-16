import {
  Entity,
  Property,
  Enum,
  Check,
  OptionalProps,
} from '@mikro-orm/core';


import { ChargeStatus, ChargeStatusStorage } from '../../../enums/charge-status.enum';
import { BaseEntity } from './base-entity.entity';

@Check({ name: "ck_card_charges_reference_max_length", expression: "(char_length(\"reference\") \u003c= 80)" })
@Check({ name: "ck_card_charges_currency_max_length", expression: "(char_length(\"currency\") \u003c= 3)" })
@Check({ name: "ck_card_charges_decline_reason_max_length", expression: "(char_length(\"decline_reason\") \u003c= 200)" })
@Check({ name: "ck_card_charges_charge_id_max_length", expression: "(char_length(\"charge_id\") \u003c= 40)" })
@Check({ name: "ck_card_charges_idempotency_key_max_length", expression: "(char_length(\"idempotency_key\") \u003c= 120)" })
@Entity({ tableName: 'card_charges' })
export class CardCharge extends BaseEntity {
  [OptionalProps]?: "createdAt" | "declineReason" | "id" | "updatedAt";


  @Property({ columnType: 'varchar', length: 80 })
  reference!: string;

  @Property({ columnType: 'decimal' })
  amount!: DecimalString;

  @Property({ columnType: 'varchar', length: 3 })
  currency!: string;

  @Enum({ items: ChargeStatusStorage.labels, nativeEnumName: 'charge_status', type: ChargeStatusStorage })
  status!: ChargeStatus;

  @Property({ columnType: 'varchar', fieldName: 'decline_reason', nullable: true, length: 200 })
  declineReason!: string | null;

  @Property({ columnType: 'varchar', fieldName: 'charge_id', unique: true, length: 40 })
  chargeId!: string;

  @Property({ columnType: 'varchar', fieldName: 'idempotency_key', unique: true, length: 120 })
  idempotencyKey!: string;





}
