import {
  Entity,
  Property,
  Enum,
  Index,
  Check,
  OptionalProps,
} from '@mikro-orm/core';


import { ViewingStatus, ViewingStatusStorage } from '../../../enums/viewing-status.enum';
import { BaseEntity } from './base-entity.entity';

@Index({ name: 'ix_viewings_listing_id', properties: ['listingId'] })
@Index({ name: 'ix_viewings_buyer_email', properties: ['buyerEmail'] })
@Index({ name: 'ix_viewings_agent_email', properties: ['agentEmail'] })
@Check({ name: "ck_viewings_listing_title_max_length", expression: "(char_length(\"listing_title\") \u003c= 200)" })
@Check({ name: "ck_viewings_buyer_name_max_length", expression: "(char_length(\"buyer_name\") \u003c= 200)" })
@Check({ name: "ck_viewings_agent_name_max_length", expression: "(char_length(\"agent_name\") \u003c= 200)" })
@Check({ name: "ck_viewings_note_max_length", expression: "(char_length(\"note\") \u003c= 500)" })
@Entity({ tableName: 'viewings' })
export class Viewing extends BaseEntity {
  [OptionalProps]?: "createdAt" | "id" | "note" | "reminderSent" | "status" | "updatedAt";


  @Property({ columnType: 'timestamptz', fieldName: 'starts_at' })
  startsAt!: Date;

  @Property({ columnType: 'timestamptz', fieldName: 'ends_at' })
  endsAt!: Date;

  @Property({ columnType: 'varchar', fieldName: 'listing_title', length: 200 })
  listingTitle!: string;

  @Property({ columnType: 'varchar', fieldName: 'buyer_name', length: 200 })
  buyerName!: string;

  @Enum({ items: ViewingStatusStorage.labels, nativeEnumName: 'viewing_status', type: ViewingStatusStorage })
  status: ViewingStatus = ViewingStatus.Requested;

  @Property({ columnType: 'varchar', fieldName: 'agent_name', length: 200 })
  agentName!: string;

  @Property({ columnType: 'varchar', nullable: true, length: 500 })
  note!: string | null;

  @Property({ columnType: 'uuid', fieldName: 'listing_id' })
  listingId!: string;

  @Property({ columnType: 'varchar', fieldName: 'buyer_email' })
  buyerEmail!: string;

  @Property({ columnType: 'varchar', fieldName: 'agent_email' })
  agentEmail!: string;

  @Property({ columnType: 'boolean', fieldName: 'reminder_sent', default: false })
  reminderSent: boolean = false;





}
