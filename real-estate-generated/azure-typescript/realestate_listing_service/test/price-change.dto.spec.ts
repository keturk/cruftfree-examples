import { validate, ValidationError } from 'class-validator';
import { plainToInstance } from 'class-transformer';
import { CreatePriceChangeDto } from '../src/dto/create-price-change.dto';
import { UpdatePriceChangeDto } from '../src/dto/update-price-change.dto';
import { PriceChangeResponseDto } from '../src/dto/price-change-response.dto';

type DtoClass = abstract new (...args: never[]) => object;

/** A request body carrying every create field. */
function buildValidPayload(): Record<string, unknown> {
  return {
    listingId: 'f47ac10b-58cc-4372-a567-0e02b2c3d479',
    oldPrice: '4.50',
    newPrice: '149.00',
  };
}

/** A request body carrying only the create fields the input requires. */
function buildRequiredPayload(): Record<string, unknown> {
  return {
    listingId: 'f47ac10b-58cc-4372-a567-0e02b2c3d479',
    oldPrice: '4.50',
    newPrice: '149.00',
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

describe('CreatePriceChangeDto', () => {
  it("entity_schema/listingDb/PriceChange/create_valid", async () => {
    const dto = readAs(CreatePriceChangeDto, buildValidPayload());
    expect(await validate(dto)).toHaveLength(0);
  });

  it("entity_schema/listingDb/PriceChange/listingId/required", async () => {
    const payload = buildValidPayload();
    delete payload['listingId'];
    const dto = readAs(CreatePriceChangeDto, payload);
    expect((await errorsOn(dto, 'listingId')).length).toBeGreaterThan(0);
  });

  it("entity_schema/listingDb/PriceChange/oldPrice/required", async () => {
    const payload = buildValidPayload();
    delete payload['oldPrice'];
    const dto = readAs(CreatePriceChangeDto, payload);
    expect((await errorsOn(dto, 'oldPrice')).length).toBeGreaterThan(0);
  });

  it("entity_schema/listingDb/PriceChange/newPrice/required", async () => {
    const payload = buildValidPayload();
    delete payload['newPrice'];
    const dto = readAs(CreatePriceChangeDto, payload);
    expect((await errorsOn(dto, 'newPrice')).length).toBeGreaterThan(0);
  });

  it("entity_schema/listingDb/PriceChange/createdAt/server_managed_excluded_from_create", () => {
    expect(declaredProperties(CreatePriceChangeDto)).not.toContain('createdAt');
  });

  it("entity_schema/listingDb/PriceChange/createdAt/server_managed_excluded_from_update", () => {
    expect(declaredProperties(UpdatePriceChangeDto)).not.toContain('createdAt');
  });

  it("entity_schema/listingDb/PriceChange/createdAt/server_managed_in_response", () => {
    expect(declaredProperties(PriceChangeResponseDto)).toContain('createdAt');
  });

  it("entity_schema/listingDb/PriceChange/updatedAt/server_managed_excluded_from_create", () => {
    expect(declaredProperties(CreatePriceChangeDto)).not.toContain('updatedAt');
  });

  it("entity_schema/listingDb/PriceChange/updatedAt/server_managed_excluded_from_update", () => {
    expect(declaredProperties(UpdatePriceChangeDto)).not.toContain('updatedAt');
  });

  it("entity_schema/listingDb/PriceChange/updatedAt/server_managed_in_response", () => {
    expect(declaredProperties(PriceChangeResponseDto)).toContain('updatedAt');
  });

  it("entity_schema/listingDb/PriceChange/id/server_managed_excluded_from_create", () => {
    expect(declaredProperties(CreatePriceChangeDto)).not.toContain('id');
  });

  it("entity_schema/listingDb/PriceChange/id/server_managed_excluded_from_update", () => {
    expect(declaredProperties(UpdatePriceChangeDto)).not.toContain('id');
  });

  it("entity_schema/listingDb/PriceChange/id/server_managed_in_response", () => {
    expect(declaredProperties(PriceChangeResponseDto)).toContain('id');
  });

  it("entity_schema/listingDb/PriceChange/listingId/immutable_in_create", () => {
    expect(declaredProperties(CreatePriceChangeDto)).toContain('listingId');
  });

  it("entity_schema/listingDb/PriceChange/listingId/immutable_excluded_from_update", () => {
    expect(declaredProperties(UpdatePriceChangeDto)).not.toContain('listingId');
  });

  it("entity_schema/listingDb/PriceChange/oldPrice/immutable_in_create", () => {
    expect(declaredProperties(CreatePriceChangeDto)).toContain('oldPrice');
  });

  it("entity_schema/listingDb/PriceChange/oldPrice/immutable_excluded_from_update", () => {
    expect(declaredProperties(UpdatePriceChangeDto)).not.toContain('oldPrice');
  });

  it("entity_schema/listingDb/PriceChange/newPrice/immutable_in_create", () => {
    expect(declaredProperties(CreatePriceChangeDto)).toContain('newPrice');
  });

  it("entity_schema/listingDb/PriceChange/newPrice/immutable_excluded_from_update", () => {
    expect(declaredProperties(UpdatePriceChangeDto)).not.toContain('newPrice');
  });

});

describe('UpdatePriceChangeDto', () => {
  it("entity_schema/listingDb/PriceChange/update_all_optional", async () => {
    const dto = readAs(UpdatePriceChangeDto, {});
    expect(await validate(dto)).toHaveLength(0);
  });

  it("entity_schema/listingDb/PriceChange/partial_update", async () => {
    const dto = readAs(UpdatePriceChangeDto, {});
    expect(dto).toBeDefined();
  });
});

describe('PriceChangeResponseDto', () => {
  it("entity_schema/listingDb/PriceChange/response_from_attributes", () => {
    const source = buildValidPayload();
    const response = readAs(PriceChangeResponseDto, source) as Record<string, unknown>;
    expect(response['listingId']).toEqual(source['listingId']);
    expect(response['oldPrice']).toEqual(source['oldPrice']);
    expect(response['newPrice']).toEqual(source['newPrice']);
  });
});
