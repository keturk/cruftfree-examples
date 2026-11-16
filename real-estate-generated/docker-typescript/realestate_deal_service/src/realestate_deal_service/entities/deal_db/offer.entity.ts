import {
  Entity,
  Property,
  Enum,
  Index,
  Check,
  OptionalProps,
} from '@mikro-orm/core';


import { Financing, FinancingStorage } from '../../../enums/financing.enum';
import { OfferStatus, OfferStatusStorage } from '../../../enums/offer-status.enum';
import { BaseEntity } from './base-entity.entity';

@Index({ name: 'ix_offers_listing_id', properties: ['listingId'] })
@Index({ name: 'ix_offers_buyer_email', properties: ['buyerEmail'] })
@Index({ name: 'ix_offers_agent_email', properties: ['agentEmail'] })
@Check({ name: "ck_offers_listing_title_max_length", expression: "(char_length(\"listing_title\") \u003c= 200)" })
@Check({ name: "ck_offers_buyer_name_max_length", expression: "(char_length(\"buyer_name\") \u003c= 200)" })
@Check({ name: "ck_offers_lender_reference_max_length", expression: "(char_length(\"lender_reference\") \u003c= 40)" })
@Entity({ tableName: 'offers' })
export class Offer extends BaseEntity {
  [OptionalProps]?: "createdAt" | "id" | "lenderReference" | "status" | "updatedAt";


  @Property({ columnType: 'varchar', fieldName: 'listing_title', length: 200 })
  listingTitle!: string;

  @Property({ columnType: 'varchar', fieldName: 'buyer_name', length: 200 })
  buyerName!: string;

  @Property({ columnType: 'decimal' })
  amount!: DecimalString;

  @Enum({ items: FinancingStorage.labels, nativeEnumName: 'financing', type: FinancingStorage })
  financing!: Financing;

  @Enum({ items: OfferStatusStorage.labels, nativeEnumName: 'offer_status', type: OfferStatusStorage })
  status: OfferStatus = OfferStatus.Submitted;

  @Property({ columnType: 'varchar', fieldName: 'lender_reference', nullable: true, length: 40 })
  lenderReference!: string | null;

  @Property({ columnType: 'uuid', fieldName: 'listing_id' })
  listingId!: string;

  @Property({ columnType: 'varchar', fieldName: 'buyer_email' })
  buyerEmail!: string;

  @Property({ columnType: 'varchar', fieldName: 'agent_email' })
  agentEmail!: string;





}
