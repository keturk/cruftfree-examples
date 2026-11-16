import {
  Entity,
  Property,
  Enum,
  Check,
  OptionalProps,
} from '@mikro-orm/core';


import { PreapprovalDecision, PreapprovalDecisionStorage } from '../../../enums/preapproval-decision.enum';
import { BaseEntity } from './base-entity.entity';

@Check({ name: "ck_lender_answers_applicant_name_max_length", expression: "(char_length(\"applicant_name\") \u003c= 200)" })
@Check({ name: "ck_lender_answers_reference_max_length", expression: "(char_length(\"reference\") \u003c= 40)" })
@Check({ name: "ck_lender_answers_idempotency_key_max_length", expression: "(char_length(\"idempotency_key\") \u003c= 120)" })
@Entity({ tableName: 'lender_answers' })
export class LenderAnswer extends BaseEntity {
  [OptionalProps]?: "createdAt" | "id" | "updatedAt";


  @Property({ columnType: 'varchar', fieldName: 'applicant_name', length: 200 })
  applicantName!: string;

  @Property({ columnType: 'decimal' })
  amount!: DecimalString;

  @Enum({ items: PreapprovalDecisionStorage.labels, nativeEnumName: 'preapproval_decision', type: PreapprovalDecisionStorage })
  decision!: PreapprovalDecision;

  @Property({ columnType: 'varchar', unique: true, length: 40 })
  reference!: string;

  @Property({ columnType: 'varchar', fieldName: 'idempotency_key', unique: true, length: 120 })
  idempotencyKey!: string;

  @Property({ columnType: 'varchar', fieldName: 'applicant_email' })
  applicantEmail!: string;





}
