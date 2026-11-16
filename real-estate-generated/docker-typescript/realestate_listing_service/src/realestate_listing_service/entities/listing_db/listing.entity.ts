import {
  Entity,
  Property,
  Enum,
  Index,
  Check,
  OptionalProps,
} from '@mikro-orm/core';


import { PropertyKind, PropertyKindStorage } from '../../../enums/property-kind.enum';
import { ListingStatus, ListingStatusStorage } from '../../../enums/listing-status.enum';
import { BaseEntity } from './base-entity.entity';

@Index({ name: 'ix_listings_status', properties: ['status'] })
@Index({ name: 'ix_listings_agent_email', properties: ['agentEmail'] })
@Check({ name: "ck_listings_title_max_length", expression: "(char_length(\"title\") \u003c= 200)" })
@Check({ name: "ck_listings_neighbourhood_name_max_length", expression: "(char_length(\"neighbourhood_name\") \u003c= 120)" })
@Check({ name: "ck_listings_agent_name_max_length", expression: "(char_length(\"agent_name\") \u003c= 200)" })
@Check({ name: "ck_listings_city_max_length", expression: "(char_length(\"city\") \u003c= 120)" })
@Entity({ tableName: 'listings' })
export class Listing extends BaseEntity {
  [OptionalProps]?: "createdAt" | "id" | "publishedAt" | "status" | "updatedAt";


  @Property({ columnType: 'varchar', length: 200 })
  title!: string;

  @Property({ columnType: 'varchar', fieldName: 'neighbourhood_name', length: 120 })
  neighbourhoodName!: string;

  @Enum({ items: PropertyKindStorage.labels, nativeEnumName: 'property_kind', type: PropertyKindStorage })
  kind!: PropertyKind;

  @Property({ columnType: 'decimal' })
  price!: DecimalString;

  @Property({ columnType: 'int' })
  bedrooms!: number;

  @Property({ columnType: 'int' })
  bathrooms!: number;

  @Property({ columnType: 'int', fieldName: 'area_sqm' })
  areaSqm!: number;

  @Enum({ items: ListingStatusStorage.labels, nativeEnumName: 'listing_status', type: ListingStatusStorage })
  status: ListingStatus = ListingStatus.Draft;

  @Property({ columnType: 'varchar', fieldName: 'agent_name', length: 200 })
  agentName!: string;

  @Property({ columnType: 'timestamptz', fieldName: 'published_at', nullable: true })
  publishedAt!: Date | null;

  @Property({ columnType: 'text' })
  summary!: string;

  @Property({ columnType: 'varchar', length: 120 })
  city!: string;

  @Property({ columnType: 'float' })
  latitude!: number;

  @Property({ columnType: 'float' })
  longitude!: number;

  @Property({ columnType: 'varchar', fieldName: 'agent_email' })
  agentEmail!: string;





}
