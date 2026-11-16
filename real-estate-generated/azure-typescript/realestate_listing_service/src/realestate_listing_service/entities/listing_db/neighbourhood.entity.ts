import {
  Entity,
  Property,
  Check,
  OptionalProps,
} from '@mikro-orm/core';


import { BaseEntity } from './base-entity.entity';

@Check({ name: "ck_neighbourhoods_name_max_length", expression: "(char_length(\"name\") \u003c= 120)" })
@Check({ name: "ck_neighbourhoods_city_max_length", expression: "(char_length(\"city\") \u003c= 120)" })
@Entity({ tableName: 'neighbourhoods' })
export class Neighbourhood extends BaseEntity {
  [OptionalProps]?: "createdAt" | "id" | "updatedAt";


  @Property({ columnType: 'varchar', unique: true, length: 120 })
  name!: string;

  @Property({ columnType: 'varchar', length: 120 })
  city!: string;

  @Property({ columnType: 'float' })
  latitude!: number;

  @Property({ columnType: 'float' })
  longitude!: number;





}
