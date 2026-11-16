import { validate, ValidationError } from 'class-validator';
import { plainToInstance } from 'class-transformer';
import { CreateApiKeyDto } from '../src/dto/create-api-key.dto';
import { UpdateApiKeyDto } from '../src/dto/update-api-key.dto';
import { ApiKeyResponseDto } from '../src/dto/api-key-response.dto';

type DtoClass = abstract new (...args: never[]) => object;

/** A request body carrying every create field. */
function buildValidPayload(): Record<string, unknown> {
  return {
    keyHash: `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`,
    ownerId: 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
    scopes: ['test_string'],
    isActive: true,
    expiresAt: new Date('2024-06-20T08:30:00Z'),
    lastUsedAt: new Date('2025-03-10T16:45:00Z'),
  };
}

/** A request body carrying only the create fields the input requires. */
function buildRequiredPayload(): Record<string, unknown> {
  return {
    keyHash: `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`,
    ownerId: 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
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

describe('CreateApiKeyDto', () => {
  it("entity_schema/channelDb/ApiKey/create_valid", async () => {
    const dto = readAs(CreateApiKeyDto, buildValidPayload());
    expect(await validate(dto)).toHaveLength(0);
  });

  it("entity_schema/channelDb/ApiKey/keyHash/required", async () => {
    const payload = buildValidPayload();
    delete payload['keyHash'];
    const dto = readAs(CreateApiKeyDto, payload);
    expect((await errorsOn(dto, 'keyHash')).length).toBeGreaterThan(0);
  });

  it("entity_schema/channelDb/ApiKey/ownerId/required", async () => {
    const payload = buildValidPayload();
    delete payload['ownerId'];
    const dto = readAs(CreateApiKeyDto, payload);
    expect((await errorsOn(dto, 'ownerId')).length).toBeGreaterThan(0);
  });

  it("entity_schema/channelDb/ApiKey/keyHash/rejects_over_max_length", async () => {
    const payload = buildValidPayload();
    payload['keyHash'] = 'x'.repeat(65);
    const dto = readAs(CreateApiKeyDto, payload);
    expect((await errorsOn(dto, 'keyHash')).length).toBeGreaterThan(0);
  });

  it("entity_schema/channelDb/ApiKey/keyHash/accepts_at_max_length", async () => {
    const payload = buildValidPayload();
    const value = 'x'.repeat(64);
    payload['keyHash'] = value;
    const dto = readAs(CreateApiKeyDto, payload);
    expect(await errorsOn(dto, 'keyHash')).toHaveLength(0);
    expect(String((dto as Record<string, unknown>)['keyHash']).length).toBe(value.length);
  });

  it("entity_schema/channelDb/ApiKey/createdAt/server_managed_excluded_from_create", () => {
    expect(declaredProperties(CreateApiKeyDto)).not.toContain('createdAt');
  });

  it("entity_schema/channelDb/ApiKey/createdAt/server_managed_excluded_from_update", () => {
    expect(declaredProperties(UpdateApiKeyDto)).not.toContain('createdAt');
  });

  it("entity_schema/channelDb/ApiKey/createdAt/server_managed_in_response", () => {
    expect(declaredProperties(ApiKeyResponseDto)).toContain('createdAt');
  });

  it("entity_schema/channelDb/ApiKey/updatedAt/server_managed_excluded_from_create", () => {
    expect(declaredProperties(CreateApiKeyDto)).not.toContain('updatedAt');
  });

  it("entity_schema/channelDb/ApiKey/updatedAt/server_managed_excluded_from_update", () => {
    expect(declaredProperties(UpdateApiKeyDto)).not.toContain('updatedAt');
  });

  it("entity_schema/channelDb/ApiKey/updatedAt/server_managed_in_response", () => {
    expect(declaredProperties(ApiKeyResponseDto)).toContain('updatedAt');
  });

  it("entity_schema/channelDb/ApiKey/id/server_managed_excluded_from_create", () => {
    expect(declaredProperties(CreateApiKeyDto)).not.toContain('id');
  });

  it("entity_schema/channelDb/ApiKey/id/server_managed_excluded_from_update", () => {
    expect(declaredProperties(UpdateApiKeyDto)).not.toContain('id');
  });

  it("entity_schema/channelDb/ApiKey/id/server_managed_in_response", () => {
    expect(declaredProperties(ApiKeyResponseDto)).toContain('id');
  });

  it("entity_schema/channelDb/ApiKey/scopes/default_applied", () => {
    const payload = buildRequiredPayload();
    delete payload['scopes'];
    const dto = readAs(CreateApiKeyDto, payload);
    expect((dto as Record<string, unknown>)['scopes']).toEqual([]);
  });

  it("entity_schema/channelDb/ApiKey/isActive/default_applied", () => {
    const payload = buildRequiredPayload();
    delete payload['isActive'];
    const dto = readAs(CreateApiKeyDto, payload);
    expect((dto as Record<string, unknown>)['isActive']).toEqual(true);
  });

});

describe('UpdateApiKeyDto', () => {
  it("entity_schema/channelDb/ApiKey/update_all_optional", async () => {
    const dto = readAs(UpdateApiKeyDto, {});
    expect(await validate(dto)).toHaveLength(0);
    expect((dto as Record<string, unknown>)['keyHash']).toBeUndefined();
    expect((dto as Record<string, unknown>)['ownerId']).toBeUndefined();
    expect((dto as Record<string, unknown>)['scopes']).toBeUndefined();
    expect((dto as Record<string, unknown>)['isActive']).toBeUndefined();
    expect((dto as Record<string, unknown>)['expiresAt']).toBeUndefined();
    expect((dto as Record<string, unknown>)['lastUsedAt']).toBeUndefined();
  });

  it("entity_schema/channelDb/ApiKey/partial_update", async () => {
    const value = `alt_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`;
    const dto = readAs(UpdateApiKeyDto, { keyHash: value });
    expect(await errorsOn(dto, 'keyHash')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['keyHash']).toEqual(value);
  });
});

describe('ApiKeyResponseDto', () => {
  it("entity_schema/channelDb/ApiKey/response_from_attributes", () => {
    const source = buildValidPayload();
    const response = readAs(ApiKeyResponseDto, source) as Record<string, unknown>;
    expect(response['keyHash']).toEqual(source['keyHash']);
    expect(response['ownerId']).toEqual(source['ownerId']);
    expect(response['scopes']).toEqual(source['scopes']);
    expect(response['isActive']).toEqual(source['isActive']);
    expect(response['expiresAt']).toEqual(source['expiresAt']);
    expect(response['lastUsedAt']).toEqual(source['lastUsedAt']);
  });
});
