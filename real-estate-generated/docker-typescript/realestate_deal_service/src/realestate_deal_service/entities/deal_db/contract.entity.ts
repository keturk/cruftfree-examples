import {
  Entity,
  Property,
  Enum,
  Index,
  Check,
  OptionalProps,
} from '@mikro-orm/core';


import { ContractStatus, ContractStatusStorage } from '../../../enums/contract-status.enum';
import { BaseEntity } from './base-entity.entity';

@Index({ name: 'ix_contracts_buyer_email', properties: ['buyerEmail'] })
@Index({ name: 'ix_contracts_agent_email', properties: ['agentEmail'] })
@Check({ name: "ck_contracts_listing_title_max_length", expression: "(char_length(\"listing_title\") \u003c= 200)" })
@Check({ name: "ck_contracts_buyer_name_max_length", expression: "(char_length(\"buyer_name\") \u003c= 200)" })
@Check({ name: "ck_contracts_envelope_id_max_length", expression: "(char_length(\"envelope_id\") \u003c= 40)" })
@Entity({ tableName: 'contracts' })
export class Contract extends BaseEntity {
  [OptionalProps]?: "createdAt" | "envelopeId" | "id" | "signedAt" | "status" | "updatedAt";


  @Property({ columnType: 'varchar', fieldName: 'listing_title', length: 200 })
  listingTitle!: string;

  @Property({ columnType: 'varchar', fieldName: 'buyer_name', length: 200 })
  buyerName!: string;

  @Property({ columnType: 'decimal' })
  price!: DecimalString;

  @Enum({ items: ContractStatusStorage.labels, nativeEnumName: 'contract_status', type: ContractStatusStorage })
  status: ContractStatus = ContractStatus.AwaitingSignature;

  @Property({ columnType: 'timestamptz', fieldName: 'signed_at', nullable: true })
  signedAt!: Date | null;

  @Property({ columnType: 'varchar', fieldName: 'envelope_id', nullable: true, length: 40 })
  envelopeId!: string | null;

  @Property({ columnType: 'uuid', fieldName: 'listing_id', unique: true })
  listingId!: string;

  @Property({ columnType: 'uuid', fieldName: 'offer_id' })
  offerId!: string;

  @Property({ columnType: 'varchar', fieldName: 'buyer_email' })
  buyerEmail!: string;

  @Property({ columnType: 'varchar', fieldName: 'agent_email' })
  agentEmail!: string;





}
