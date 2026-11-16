import {
  Entity,
  Property,
  Enum,
  Check,
  OptionalProps,
} from '@mikro-orm/core';


import { EnvelopeStatus, EnvelopeStatusStorage } from '../../../enums/envelope-status.enum';
import { BaseEntity } from './base-entity.entity';

@Check({ name: "ck_vendor_envelopes_signer_name_max_length", expression: "(char_length(\"signer_name\") \u003c= 200)" })
@Check({ name: "ck_vendor_envelopes_document_title_max_length", expression: "(char_length(\"document_title\") \u003c= 200)" })
@Check({ name: "ck_vendor_envelopes_envelope_id_max_length", expression: "(char_length(\"envelope_id\") \u003c= 40)" })
@Check({ name: "ck_vendor_envelopes_idempotency_key_max_length", expression: "(char_length(\"idempotency_key\") \u003c= 120)" })
@Entity({ tableName: 'vendor_envelopes' })
export class VendorEnvelope extends BaseEntity {
  [OptionalProps]?: "createdAt" | "id" | "settledAt" | "status" | "updatedAt";


  @Property({ columnType: 'varchar', fieldName: 'signer_name', length: 200 })
  signerName!: string;

  @Property({ columnType: 'varchar', fieldName: 'document_title', length: 200 })
  documentTitle!: string;

  @Enum({ items: EnvelopeStatusStorage.labels, nativeEnumName: 'envelope_status', type: EnvelopeStatusStorage })
  status: EnvelopeStatus = EnvelopeStatus.Sent;

  @Property({ columnType: 'timestamptz', fieldName: 'settled_at', nullable: true })
  settledAt!: Date | null;

  @Property({ columnType: 'text', fieldName: 'document_body' })
  documentBody!: string;

  @Property({ columnType: 'varchar', fieldName: 'signer_email' })
  signerEmail!: string;

  @Property({ columnType: 'varchar', fieldName: 'envelope_id', unique: true, length: 40 })
  envelopeId!: string;

  @Property({ columnType: 'varchar', fieldName: 'idempotency_key', unique: true, length: 120 })
  idempotencyKey!: string;





}
