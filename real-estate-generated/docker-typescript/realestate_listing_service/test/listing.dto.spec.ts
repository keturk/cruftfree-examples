import { validate, ValidationError } from 'class-validator';
import { plainToInstance } from 'class-transformer';
import { CreateListingDto } from '../src/dto/create-listing.dto';
import { UpdateListingDto } from '../src/dto/update-listing.dto';
import { ListingResponseDto } from '../src/dto/listing-response.dto';
import { PropertyKind } from '../src/enums/property-kind.enum';
import { ListingStatus } from '../src/enums/listing-status.enum';

type DtoClass = abstract new (...args: never[]) => object;

/** A request body carrying every create field. */
function buildValidPayload(): Record<string, unknown> {
  return {
    title: 'foo_bar',
    neighbourhoodName: 'sample_text',
    kind: PropertyKind.House,
    price: '49.95',
    bedrooms: 42,
    bathrooms: 42,
    areaSqm: 7,
    status: ListingStatus.Draft,
    agentName: 'sample_text',
    publishedAt: new Date('2025-01-15T12:00:00Z'),
    summary: 'Test content body with details',
    city: 'foo_bar',
    latitude: 2.718,
    longitude: 0.5,
    agentEmail: 'hello@world.com',
  };
}

/** A request body carrying only the create fields the input requires. */
function buildRequiredPayload(): Record<string, unknown> {
  return {
    title: 'foo_bar',
    neighbourhoodName: 'sample_text',
    kind: PropertyKind.House,
    price: '49.95',
    bedrooms: 42,
    bathrooms: 42,
    areaSqm: 7,
    agentName: 'sample_text',
    summary: 'Test content body with details',
    city: 'foo_bar',
    latitude: 2.718,
    longitude: 0.5,
    agentEmail: 'hello@world.com',
  };
}

/** The validation errors one property of *dto* raises. */
async function errorsOn(dto: object, property: string): Promise<ValidationError[]> {
  return (await validate(dto)).filter((error) => error.property === property);
}

/** The properties a DTO class declares (its OpenAPI property list). */
function declaredProperties(dto: DtoClass): string[] {
  const names = Reflect.getMetadata('swagger/apiModelPropertiesArray', dto.prototype) as
    | string[]
    | undefined;
  if (names === undefined) {
    throw new Error(`${dto.name} declares no documented property.`);
  }
  return names.map((name) => name.replace(/^:/, ''));
}

/** *payload* through *dto*, as a request body is read. */
function readAs<T extends object>(dto: new () => T, payload: Record<string, unknown>): T {
  return plainToInstance(dto, payload);
}

describe('CreateListingDto', () => {
  it("entity_schema/listingDb/Listing/create_valid", async () => {
    const dto = readAs(CreateListingDto, buildValidPayload());
    expect(await validate(dto)).toHaveLength(0);
  });

  it("entity_schema/listingDb/Listing/title/required", async () => {
    const payload = buildValidPayload();
    delete payload['title'];
    const dto = readAs(CreateListingDto, payload);
    expect((await errorsOn(dto, 'title')).length).toBeGreaterThan(0);
  });

  it("entity_schema/listingDb/Listing/neighbourhoodName/required", async () => {
    const payload = buildValidPayload();
    delete payload['neighbourhoodName'];
    const dto = readAs(CreateListingDto, payload);
    expect((await errorsOn(dto, 'neighbourhoodName')).length).toBeGreaterThan(0);
  });

  it("entity_schema/listingDb/Listing/kind/required", async () => {
    const payload = buildValidPayload();
    delete payload['kind'];
    const dto = readAs(CreateListingDto, payload);
    expect((await errorsOn(dto, 'kind')).length).toBeGreaterThan(0);
  });

  it("entity_schema/listingDb/Listing/price/required", async () => {
    const payload = buildValidPayload();
    delete payload['price'];
    const dto = readAs(CreateListingDto, payload);
    expect((await errorsOn(dto, 'price')).length).toBeGreaterThan(0);
  });

  it("entity_schema/listingDb/Listing/bedrooms/required", async () => {
    const payload = buildValidPayload();
    delete payload['bedrooms'];
    const dto = readAs(CreateListingDto, payload);
    expect((await errorsOn(dto, 'bedrooms')).length).toBeGreaterThan(0);
  });

  it("entity_schema/listingDb/Listing/bathrooms/required", async () => {
    const payload = buildValidPayload();
    delete payload['bathrooms'];
    const dto = readAs(CreateListingDto, payload);
    expect((await errorsOn(dto, 'bathrooms')).length).toBeGreaterThan(0);
  });

  it("entity_schema/listingDb/Listing/areaSqm/required", async () => {
    const payload = buildValidPayload();
    delete payload['areaSqm'];
    const dto = readAs(CreateListingDto, payload);
    expect((await errorsOn(dto, 'areaSqm')).length).toBeGreaterThan(0);
  });

  it("entity_schema/listingDb/Listing/agentName/required", async () => {
    const payload = buildValidPayload();
    delete payload['agentName'];
    const dto = readAs(CreateListingDto, payload);
    expect((await errorsOn(dto, 'agentName')).length).toBeGreaterThan(0);
  });

  it("entity_schema/listingDb/Listing/summary/required", async () => {
    const payload = buildValidPayload();
    delete payload['summary'];
    const dto = readAs(CreateListingDto, payload);
    expect((await errorsOn(dto, 'summary')).length).toBeGreaterThan(0);
  });

  it("entity_schema/listingDb/Listing/city/required", async () => {
    const payload = buildValidPayload();
    delete payload['city'];
    const dto = readAs(CreateListingDto, payload);
    expect((await errorsOn(dto, 'city')).length).toBeGreaterThan(0);
  });

  it("entity_schema/listingDb/Listing/latitude/required", async () => {
    const payload = buildValidPayload();
    delete payload['latitude'];
    const dto = readAs(CreateListingDto, payload);
    expect((await errorsOn(dto, 'latitude')).length).toBeGreaterThan(0);
  });

  it("entity_schema/listingDb/Listing/longitude/required", async () => {
    const payload = buildValidPayload();
    delete payload['longitude'];
    const dto = readAs(CreateListingDto, payload);
    expect((await errorsOn(dto, 'longitude')).length).toBeGreaterThan(0);
  });

  it("entity_schema/listingDb/Listing/agentEmail/required", async () => {
    const payload = buildValidPayload();
    delete payload['agentEmail'];
    const dto = readAs(CreateListingDto, payload);
    expect((await errorsOn(dto, 'agentEmail')).length).toBeGreaterThan(0);
  });

  it("entity_schema/listingDb/Listing/title/rejects_over_max_length", async () => {
    const payload = buildValidPayload();
    payload['title'] = 'x'.repeat(201);
    const dto = readAs(CreateListingDto, payload);
    expect((await errorsOn(dto, 'title')).length).toBeGreaterThan(0);
  });

  it("entity_schema/listingDb/Listing/title/accepts_at_max_length", async () => {
    const payload = buildValidPayload();
    const value = 'x'.repeat(200);
    payload['title'] = value;
    const dto = readAs(CreateListingDto, payload);
    expect(await errorsOn(dto, 'title')).toHaveLength(0);
    expect(String((dto as Record<string, unknown>)['title']).length).toBe(value.length);
  });

  it("entity_schema/listingDb/Listing/neighbourhoodName/rejects_over_max_length", async () => {
    const payload = buildValidPayload();
    payload['neighbourhoodName'] = 'x'.repeat(121);
    const dto = readAs(CreateListingDto, payload);
    expect((await errorsOn(dto, 'neighbourhoodName')).length).toBeGreaterThan(0);
  });

  it("entity_schema/listingDb/Listing/neighbourhoodName/accepts_at_max_length", async () => {
    const payload = buildValidPayload();
    const value = 'x'.repeat(120);
    payload['neighbourhoodName'] = value;
    const dto = readAs(CreateListingDto, payload);
    expect(await errorsOn(dto, 'neighbourhoodName')).toHaveLength(0);
    expect(String((dto as Record<string, unknown>)['neighbourhoodName']).length).toBe(value.length);
  });

  it("entity_schema/listingDb/Listing/agentName/rejects_over_max_length", async () => {
    const payload = buildValidPayload();
    payload['agentName'] = 'x'.repeat(201);
    const dto = readAs(CreateListingDto, payload);
    expect((await errorsOn(dto, 'agentName')).length).toBeGreaterThan(0);
  });

  it("entity_schema/listingDb/Listing/agentName/accepts_at_max_length", async () => {
    const payload = buildValidPayload();
    const value = 'x'.repeat(200);
    payload['agentName'] = value;
    const dto = readAs(CreateListingDto, payload);
    expect(await errorsOn(dto, 'agentName')).toHaveLength(0);
    expect(String((dto as Record<string, unknown>)['agentName']).length).toBe(value.length);
  });

  it("entity_schema/listingDb/Listing/city/rejects_over_max_length", async () => {
    const payload = buildValidPayload();
    payload['city'] = 'x'.repeat(121);
    const dto = readAs(CreateListingDto, payload);
    expect((await errorsOn(dto, 'city')).length).toBeGreaterThan(0);
  });

  it("entity_schema/listingDb/Listing/city/accepts_at_max_length", async () => {
    const payload = buildValidPayload();
    const value = 'x'.repeat(120);
    payload['city'] = value;
    const dto = readAs(CreateListingDto, payload);
    expect(await errorsOn(dto, 'city')).toHaveLength(0);
    expect(String((dto as Record<string, unknown>)['city']).length).toBe(value.length);
  });

  it("entity_schema/listingDb/Listing/createdAt/server_managed_excluded_from_create", () => {
    expect(declaredProperties(CreateListingDto)).not.toContain('createdAt');
  });

  it("entity_schema/listingDb/Listing/createdAt/server_managed_excluded_from_update", () => {
    expect(declaredProperties(UpdateListingDto)).not.toContain('createdAt');
  });

  it("entity_schema/listingDb/Listing/createdAt/server_managed_in_response", () => {
    expect(declaredProperties(ListingResponseDto)).toContain('createdAt');
  });

  it("entity_schema/listingDb/Listing/updatedAt/server_managed_excluded_from_create", () => {
    expect(declaredProperties(CreateListingDto)).not.toContain('updatedAt');
  });

  it("entity_schema/listingDb/Listing/updatedAt/server_managed_excluded_from_update", () => {
    expect(declaredProperties(UpdateListingDto)).not.toContain('updatedAt');
  });

  it("entity_schema/listingDb/Listing/updatedAt/server_managed_in_response", () => {
    expect(declaredProperties(ListingResponseDto)).toContain('updatedAt');
  });

  it("entity_schema/listingDb/Listing/id/server_managed_excluded_from_create", () => {
    expect(declaredProperties(CreateListingDto)).not.toContain('id');
  });

  it("entity_schema/listingDb/Listing/id/server_managed_excluded_from_update", () => {
    expect(declaredProperties(UpdateListingDto)).not.toContain('id');
  });

  it("entity_schema/listingDb/Listing/id/server_managed_in_response", () => {
    expect(declaredProperties(ListingResponseDto)).toContain('id');
  });

  it("entity_schema/listingDb/Listing/status/default_applied", () => {
    const payload = buildRequiredPayload();
    delete payload['status'];
    const dto = readAs(CreateListingDto, payload);
    expect((dto as Record<string, unknown>)['status']).toEqual(ListingStatus.Draft);
  });

});

describe('CreateListingDto kind enum', () => {
  it("entity_schema/listingDb/Listing/kind/House/enum_accepts", async () => {
    const payload = buildValidPayload();
    payload['kind'] = PropertyKind.House;
    const dto = readAs(CreateListingDto, payload);
    expect(await errorsOn(dto, 'kind')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['kind']).toBe(PropertyKind.House);
  });

  it("entity_schema/listingDb/Listing/kind/House/enum_coerces_string", async () => {
    const payload = buildValidPayload();
    payload['kind'] = 'House';
    const dto = readAs(CreateListingDto, payload);
    expect(await errorsOn(dto, 'kind')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['kind']).toBe(PropertyKind.House);
  });

  it("entity_schema/listingDb/Listing/kind/Apartment/enum_accepts", async () => {
    const payload = buildValidPayload();
    payload['kind'] = PropertyKind.Apartment;
    const dto = readAs(CreateListingDto, payload);
    expect(await errorsOn(dto, 'kind')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['kind']).toBe(PropertyKind.Apartment);
  });

  it("entity_schema/listingDb/Listing/kind/Apartment/enum_coerces_string", async () => {
    const payload = buildValidPayload();
    payload['kind'] = 'Apartment';
    const dto = readAs(CreateListingDto, payload);
    expect(await errorsOn(dto, 'kind')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['kind']).toBe(PropertyKind.Apartment);
  });

  it("entity_schema/listingDb/Listing/kind/Townhouse/enum_accepts", async () => {
    const payload = buildValidPayload();
    payload['kind'] = PropertyKind.Townhouse;
    const dto = readAs(CreateListingDto, payload);
    expect(await errorsOn(dto, 'kind')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['kind']).toBe(PropertyKind.Townhouse);
  });

  it("entity_schema/listingDb/Listing/kind/Townhouse/enum_coerces_string", async () => {
    const payload = buildValidPayload();
    payload['kind'] = 'Townhouse';
    const dto = readAs(CreateListingDto, payload);
    expect(await errorsOn(dto, 'kind')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['kind']).toBe(PropertyKind.Townhouse);
  });

  it("entity_schema/listingDb/Listing/kind/Cottage/enum_accepts", async () => {
    const payload = buildValidPayload();
    payload['kind'] = PropertyKind.Cottage;
    const dto = readAs(CreateListingDto, payload);
    expect(await errorsOn(dto, 'kind')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['kind']).toBe(PropertyKind.Cottage);
  });

  it("entity_schema/listingDb/Listing/kind/Cottage/enum_coerces_string", async () => {
    const payload = buildValidPayload();
    payload['kind'] = 'Cottage';
    const dto = readAs(CreateListingDto, payload);
    expect(await errorsOn(dto, 'kind')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['kind']).toBe(PropertyKind.Cottage);
  });

  it("entity_schema/listingDb/Listing/kind/Land/enum_accepts", async () => {
    const payload = buildValidPayload();
    payload['kind'] = PropertyKind.Land;
    const dto = readAs(CreateListingDto, payload);
    expect(await errorsOn(dto, 'kind')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['kind']).toBe(PropertyKind.Land);
  });

  it("entity_schema/listingDb/Listing/kind/Land/enum_coerces_string", async () => {
    const payload = buildValidPayload();
    payload['kind'] = 'Land';
    const dto = readAs(CreateListingDto, payload);
    expect(await errorsOn(dto, 'kind')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['kind']).toBe(PropertyKind.Land);
  });

  it("entity_schema/listingDb/Listing/kind/enum_rejects_invalid_string", async () => {
    const payload = buildValidPayload();
    payload['kind'] = 'NotAValidMember';
    const dto = readAs(CreateListingDto, payload);
    expect((await errorsOn(dto, 'kind')).length).toBeGreaterThan(0);
  });

  it("entity_schema/listingDb/Listing/kind/enum_rejects_invalid_type", async () => {
    const payload = buildValidPayload();
    payload['kind'] = 42;
    const dto = readAs(CreateListingDto, payload);
    expect((await errorsOn(dto, 'kind')).length).toBeGreaterThan(0);
  });

  it("entity_schema/listingDb/Listing/kind/enum_in_update_optional", async () => {
    const dto = readAs(UpdateListingDto, {});
    expect((dto as Record<string, unknown>)['kind']).toBeUndefined();
    expect(await errorsOn(dto, 'kind')).toHaveLength(0);
  });
});

describe('CreateListingDto status enum', () => {
  it("entity_schema/listingDb/Listing/status/Draft/enum_accepts", async () => {
    const payload = buildValidPayload();
    payload['status'] = ListingStatus.Draft;
    const dto = readAs(CreateListingDto, payload);
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['status']).toBe(ListingStatus.Draft);
  });

  it("entity_schema/listingDb/Listing/status/Draft/enum_coerces_string", async () => {
    const payload = buildValidPayload();
    payload['status'] = 'Draft';
    const dto = readAs(CreateListingDto, payload);
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['status']).toBe(ListingStatus.Draft);
  });

  it("entity_schema/listingDb/Listing/status/Active/enum_accepts", async () => {
    const payload = buildValidPayload();
    payload['status'] = ListingStatus.Active;
    const dto = readAs(CreateListingDto, payload);
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['status']).toBe(ListingStatus.Active);
  });

  it("entity_schema/listingDb/Listing/status/Active/enum_coerces_string", async () => {
    const payload = buildValidPayload();
    payload['status'] = 'Active';
    const dto = readAs(CreateListingDto, payload);
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['status']).toBe(ListingStatus.Active);
  });

  it("entity_schema/listingDb/Listing/status/UnderOffer/enum_accepts", async () => {
    const payload = buildValidPayload();
    payload['status'] = ListingStatus.UnderOffer;
    const dto = readAs(CreateListingDto, payload);
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['status']).toBe(ListingStatus.UnderOffer);
  });

  it("entity_schema/listingDb/Listing/status/UnderOffer/enum_coerces_string", async () => {
    const payload = buildValidPayload();
    payload['status'] = 'UnderOffer';
    const dto = readAs(CreateListingDto, payload);
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['status']).toBe(ListingStatus.UnderOffer);
  });

  it("entity_schema/listingDb/Listing/status/Sold/enum_accepts", async () => {
    const payload = buildValidPayload();
    payload['status'] = ListingStatus.Sold;
    const dto = readAs(CreateListingDto, payload);
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['status']).toBe(ListingStatus.Sold);
  });

  it("entity_schema/listingDb/Listing/status/Sold/enum_coerces_string", async () => {
    const payload = buildValidPayload();
    payload['status'] = 'Sold';
    const dto = readAs(CreateListingDto, payload);
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['status']).toBe(ListingStatus.Sold);
  });

  it("entity_schema/listingDb/Listing/status/Withdrawn/enum_accepts", async () => {
    const payload = buildValidPayload();
    payload['status'] = ListingStatus.Withdrawn;
    const dto = readAs(CreateListingDto, payload);
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['status']).toBe(ListingStatus.Withdrawn);
  });

  it("entity_schema/listingDb/Listing/status/Withdrawn/enum_coerces_string", async () => {
    const payload = buildValidPayload();
    payload['status'] = 'Withdrawn';
    const dto = readAs(CreateListingDto, payload);
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['status']).toBe(ListingStatus.Withdrawn);
  });

  it("entity_schema/listingDb/Listing/status/enum_rejects_invalid_string", async () => {
    const payload = buildValidPayload();
    payload['status'] = 'NotAValidMember';
    const dto = readAs(CreateListingDto, payload);
    expect((await errorsOn(dto, 'status')).length).toBeGreaterThan(0);
  });

  it("entity_schema/listingDb/Listing/status/enum_rejects_invalid_type", async () => {
    const payload = buildValidPayload();
    payload['status'] = 42;
    const dto = readAs(CreateListingDto, payload);
    expect((await errorsOn(dto, 'status')).length).toBeGreaterThan(0);
  });

  it("entity_schema/listingDb/Listing/status/enum_default_applied_when_omitted", () => {
    const payload = buildRequiredPayload();
    delete payload['status'];
    const dto = readAs(CreateListingDto, payload);
    expect((dto as Record<string, unknown>)['status']).toEqual(ListingStatus.Draft);
  });

  it("entity_schema/listingDb/Listing/status/enum_in_update_optional", async () => {
    const dto = readAs(UpdateListingDto, {});
    expect((dto as Record<string, unknown>)['status']).toBeUndefined();
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
  });
});

describe('UpdateListingDto', () => {
  it("entity_schema/listingDb/Listing/update_all_optional", async () => {
    const dto = readAs(UpdateListingDto, {});
    expect(await validate(dto)).toHaveLength(0);
    expect((dto as Record<string, unknown>)['title']).toBeUndefined();
    expect((dto as Record<string, unknown>)['neighbourhoodName']).toBeUndefined();
    expect((dto as Record<string, unknown>)['kind']).toBeUndefined();
    expect((dto as Record<string, unknown>)['price']).toBeUndefined();
    expect((dto as Record<string, unknown>)['bedrooms']).toBeUndefined();
    expect((dto as Record<string, unknown>)['bathrooms']).toBeUndefined();
    expect((dto as Record<string, unknown>)['areaSqm']).toBeUndefined();
    expect((dto as Record<string, unknown>)['status']).toBeUndefined();
    expect((dto as Record<string, unknown>)['agentName']).toBeUndefined();
    expect((dto as Record<string, unknown>)['publishedAt']).toBeUndefined();
    expect((dto as Record<string, unknown>)['summary']).toBeUndefined();
    expect((dto as Record<string, unknown>)['city']).toBeUndefined();
    expect((dto as Record<string, unknown>)['latitude']).toBeUndefined();
    expect((dto as Record<string, unknown>)['longitude']).toBeUndefined();
    expect((dto as Record<string, unknown>)['agentEmail']).toBeUndefined();
  });

  it("entity_schema/listingDb/Listing/partial_update", async () => {
    const value = 'test_string';
    const dto = readAs(UpdateListingDto, { title: value });
    expect(await errorsOn(dto, 'title')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['title']).toEqual(value);
  });
});

describe('ListingResponseDto', () => {
  it("entity_schema/listingDb/Listing/response_from_attributes", () => {
    const source = buildValidPayload();
    const response = readAs(ListingResponseDto, source) as Record<string, unknown>;
    expect(response['title']).toEqual(source['title']);
    expect(response['neighbourhoodName']).toEqual(source['neighbourhoodName']);
    expect(response['kind']).toEqual(source['kind']);
    expect(response['price']).toEqual(source['price']);
    expect(response['bedrooms']).toEqual(source['bedrooms']);
    expect(response['bathrooms']).toEqual(source['bathrooms']);
    expect(response['areaSqm']).toEqual(source['areaSqm']);
    expect(response['status']).toEqual(source['status']);
    expect(response['agentName']).toEqual(source['agentName']);
    expect(response['publishedAt']).toEqual(source['publishedAt']);
    expect(response['summary']).toEqual(source['summary']);
    expect(response['city']).toEqual(source['city']);
    expect(response['latitude']).toEqual(source['latitude']);
    expect(response['longitude']).toEqual(source['longitude']);
    expect(response['agentEmail']).toEqual(source['agentEmail']);
  });

  it("entity_schema/listingDb/Listing/response_serializes_enum_fields", () => {
    const source: Record<string, unknown> = {
      kind: PropertyKind.House,
      status: ListingStatus.Draft,
    };
    const response = readAs(ListingResponseDto, source) as Record<string, unknown>;
    expect(response['kind']).toBe(PropertyKind.House);
    expect(response['status']).toBe(ListingStatus.Draft);
  });
});
