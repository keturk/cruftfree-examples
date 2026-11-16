import {
  Entity,
  Property,
  Index,
  OptionalProps,
} from '@mikro-orm/core';


import { BaseEntity } from './base-entity.entity';

@Index({ name: 'ix_price_changes_listing_id', properties: ['listingId'] })
@Entity({ tableName: 'price_changes' })
export class PriceChange extends BaseEntity {
  [OptionalProps]?: "createdAt" | "id" | "updatedAt";


  @Property({ columnType: 'uuid', fieldName: 'listing_id' })
  listingId!: string;

  @Property({ columnType: 'decimal', fieldName: 'old_price' })
  oldPrice!: DecimalString;

  @Property({ columnType: 'decimal', fieldName: 'new_price' })
  newPrice!: DecimalString;





}
