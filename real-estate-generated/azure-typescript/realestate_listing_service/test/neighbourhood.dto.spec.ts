import { validate, ValidationError } from 'class-validator';
import { plainToInstance } from 'class-transformer';
import { CreateNeighbourhoodDto } from '../src/dto/create-neighbourhood.dto';
import { UpdateNeighbourhoodDto } from '../src/dto/update-neighbourhood.dto';
import { NeighbourhoodResponseDto } from '../src/dto/neighbourhood-response.dto';

type DtoClass = abstract new (...args: never[]) => object;

/** A request body carrying every create field. */
function buildValidPayload(): Record<string, unknown> {
  return {
    name: `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`,
    city: 'world',
    latitude: 3.14,
    longitude: 1.0,
  };
}

/** A request body carrying only the create fields the input requires. */
function buildRequiredPayload(): Record<string, unknown> {
  return {
    name: `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`,
    city: 'world',
    latitude: 3.14,
    longitude: 1.0,
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

describe('CreateNeighbourhoodDto', () => {
  it("entity_schema/listingDb/Neighbourhood/create_valid", async () => {
    const dto = readAs(CreateNeighbourhoodDto, buildValidPayload());
    expect(await validate(dto)).toHaveLength(0);
  });

  it("entity_schema/listingDb/Neighbourhood/name/required", async () => {
    const payload = buildValidPayload();
    delete payload['name'];
    const dto = readAs(CreateNeighbourhoodDto, payload);
    expect((await errorsOn(dto, 'name')).length).toBeGreaterThan(0);
  });

  it("entity_schema/listingDb/Neighbourhood/city/required", async () => {
    const payload = buildValidPayload();
    delete payload['city'];
    const dto = readAs(CreateNeighbourhoodDto, payload);
    expect((await errorsOn(dto, 'city')).length).toBeGreaterThan(0);
  });

  it("entity_schema/listingDb/Neighbourhood/latitude/required", async () => {
    const payload = buildValidPayload();
    delete payload['latitude'];
    const dto = readAs(CreateNeighbourhoodDto, payload);
    expect((await errorsOn(dto, 'latitude')).length).toBeGreaterThan(0);
  });

  it("entity_schema/listingDb/Neighbourhood/longitude/required", async () => {
    const payload = buildValidPayload();
    delete payload['longitude'];
    const dto = readAs(CreateNeighbourhoodDto, payload);
    expect((await errorsOn(dto, 'longitude')).length).toBeGreaterThan(0);
  });

  it("entity_schema/listingDb/Neighbourhood/name/rejects_over_max_length", async () => {
    const payload = buildValidPayload();
    payload['name'] = 'x'.repeat(121);
    const dto = readAs(CreateNeighbourhoodDto, payload);
    expect((await errorsOn(dto, 'name')).length).toBeGreaterThan(0);
  });

  it("entity_schema/listingDb/Neighbourhood/name/accepts_at_max_length", async () => {
    const payload = buildValidPayload();
    const value = 'x'.repeat(120);
    payload['name'] = value;
    const dto = readAs(CreateNeighbourhoodDto, payload);
    expect(await errorsOn(dto, 'name')).toHaveLength(0);
    expect(String((dto as Record<string, unknown>)['name']).length).toBe(value.length);
  });

  it("entity_schema/listingDb/Neighbourhood/city/rejects_over_max_length", async () => {
    const payload = buildValidPayload();
    payload['city'] = 'x'.repeat(121);
    const dto = readAs(CreateNeighbourhoodDto, payload);
    expect((await errorsOn(dto, 'city')).length).toBeGreaterThan(0);
  });

  it("entity_schema/listingDb/Neighbourhood/city/accepts_at_max_length", async () => {
    const payload = buildValidPayload();
    const value = 'x'.repeat(120);
    payload['city'] = value;
    const dto = readAs(CreateNeighbourhoodDto, payload);
    expect(await errorsOn(dto, 'city')).toHaveLength(0);
    expect(String((dto as Record<string, unknown>)['city']).length).toBe(value.length);
  });

  it("entity_schema/listingDb/Neighbourhood/createdAt/server_managed_excluded_from_create", () => {
    expect(declaredProperties(CreateNeighbourhoodDto)).not.toContain('createdAt');
  });

  it("entity_schema/listingDb/Neighbourhood/createdAt/server_managed_excluded_from_update", () => {
    expect(declaredProperties(UpdateNeighbourhoodDto)).not.toContain('createdAt');
  });

  it("entity_schema/listingDb/Neighbourhood/createdAt/server_managed_in_response", () => {
    expect(declaredProperties(NeighbourhoodResponseDto)).toContain('createdAt');
  });

  it("entity_schema/listingDb/Neighbourhood/updatedAt/server_managed_excluded_from_create", () => {
    expect(declaredProperties(CreateNeighbourhoodDto)).not.toContain('updatedAt');
  });

  it("entity_schema/listingDb/Neighbourhood/updatedAt/server_managed_excluded_from_update", () => {
    expect(declaredProperties(UpdateNeighbourhoodDto)).not.toContain('updatedAt');
  });

  it("entity_schema/listingDb/Neighbourhood/updatedAt/server_managed_in_response", () => {
    expect(declaredProperties(NeighbourhoodResponseDto)).toContain('updatedAt');
  });

  it("entity_schema/listingDb/Neighbourhood/id/server_managed_excluded_from_create", () => {
    expect(declaredProperties(CreateNeighbourhoodDto)).not.toContain('id');
  });

  it("entity_schema/listingDb/Neighbourhood/id/server_managed_excluded_from_update", () => {
    expect(declaredProperties(UpdateNeighbourhoodDto)).not.toContain('id');
  });

  it("entity_schema/listingDb/Neighbourhood/id/server_managed_in_response", () => {
    expect(declaredProperties(NeighbourhoodResponseDto)).toContain('id');
  });

});

describe('UpdateNeighbourhoodDto', () => {
  it("entity_schema/listingDb/Neighbourhood/update_all_optional", async () => {
    const dto = readAs(UpdateNeighbourhoodDto, {});
    expect(await validate(dto)).toHaveLength(0);
    expect((dto as Record<string, unknown>)['name']).toBeUndefined();
    expect((dto as Record<string, unknown>)['city']).toBeUndefined();
    expect((dto as Record<string, unknown>)['latitude']).toBeUndefined();
    expect((dto as Record<string, unknown>)['longitude']).toBeUndefined();
  });

  it("entity_schema/listingDb/Neighbourhood/partial_update", async () => {
    const value = `alt_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`;
    const dto = readAs(UpdateNeighbourhoodDto, { name: value });
    expect(await errorsOn(dto, 'name')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['name']).toEqual(value);
  });
});

describe('NeighbourhoodResponseDto', () => {
  it("entity_schema/listingDb/Neighbourhood/response_from_attributes", () => {
    const source = buildValidPayload();
    const response = readAs(NeighbourhoodResponseDto, source) as Record<string, unknown>;
    expect(response['name']).toEqual(source['name']);
    expect(response['city']).toEqual(source['city']);
    expect(response['latitude']).toEqual(source['latitude']);
    expect(response['longitude']).toEqual(source['longitude']);
  });
});
