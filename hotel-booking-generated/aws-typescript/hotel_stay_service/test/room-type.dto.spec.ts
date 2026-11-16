import { validate, ValidationError } from 'class-validator';
import { plainToInstance } from 'class-transformer';
import { CreateRoomTypeDto } from '../src/dto/create-room-type.dto';
import { UpdateRoomTypeDto } from '../src/dto/update-room-type.dto';
import { RoomTypeResponseDto } from '../src/dto/room-type-response.dto';

type DtoClass = abstract new (...args: never[]) => object;

/** A request body carrying every create field. */
function buildValidPayload(): Record<string, unknown> {
  return {
    name: `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`,
    summary: 'world',
    description: 'Description text used for validation',
    sleeps: 100,
    nightlyRate: '19.99',
    inventory: 7,
    listed: false,
  };
}

/** A request body carrying only the create fields the input requires. */
function buildRequiredPayload(): Record<string, unknown> {
  return {
    name: `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`,
    summary: 'world',
    description: 'Description text used for validation',
    sleeps: 100,
    nightlyRate: '19.99',
    inventory: 7,
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

describe('CreateRoomTypeDto', () => {
  it("entity_schema/stayDb/RoomType/create_valid", async () => {
    const dto = readAs(CreateRoomTypeDto, buildValidPayload());
    expect(await validate(dto)).toHaveLength(0);
  });

  it("entity_schema/stayDb/RoomType/name/required", async () => {
    const payload = buildValidPayload();
    delete payload['name'];
    const dto = readAs(CreateRoomTypeDto, payload);
    expect((await errorsOn(dto, 'name')).length).toBeGreaterThan(0);
  });

  it("entity_schema/stayDb/RoomType/summary/required", async () => {
    const payload = buildValidPayload();
    delete payload['summary'];
    const dto = readAs(CreateRoomTypeDto, payload);
    expect((await errorsOn(dto, 'summary')).length).toBeGreaterThan(0);
  });

  it("entity_schema/stayDb/RoomType/description/required", async () => {
    const payload = buildValidPayload();
    delete payload['description'];
    const dto = readAs(CreateRoomTypeDto, payload);
    expect((await errorsOn(dto, 'description')).length).toBeGreaterThan(0);
  });

  it("entity_schema/stayDb/RoomType/sleeps/required", async () => {
    const payload = buildValidPayload();
    delete payload['sleeps'];
    const dto = readAs(CreateRoomTypeDto, payload);
    expect((await errorsOn(dto, 'sleeps')).length).toBeGreaterThan(0);
  });

  it("entity_schema/stayDb/RoomType/nightlyRate/required", async () => {
    const payload = buildValidPayload();
    delete payload['nightlyRate'];
    const dto = readAs(CreateRoomTypeDto, payload);
    expect((await errorsOn(dto, 'nightlyRate')).length).toBeGreaterThan(0);
  });

  it("entity_schema/stayDb/RoomType/inventory/required", async () => {
    const payload = buildValidPayload();
    delete payload['inventory'];
    const dto = readAs(CreateRoomTypeDto, payload);
    expect((await errorsOn(dto, 'inventory')).length).toBeGreaterThan(0);
  });

  it("entity_schema/stayDb/RoomType/name/rejects_over_max_length", async () => {
    const payload = buildValidPayload();
    payload['name'] = 'x'.repeat(81);
    const dto = readAs(CreateRoomTypeDto, payload);
    expect((await errorsOn(dto, 'name')).length).toBeGreaterThan(0);
  });

  it("entity_schema/stayDb/RoomType/name/accepts_at_max_length", async () => {
    const payload = buildValidPayload();
    const value = 'x'.repeat(80);
    payload['name'] = value;
    const dto = readAs(CreateRoomTypeDto, payload);
    expect(await errorsOn(dto, 'name')).toHaveLength(0);
    expect(String((dto as Record<string, unknown>)['name']).length).toBe(value.length);
  });

  it("entity_schema/stayDb/RoomType/summary/rejects_over_max_length", async () => {
    const payload = buildValidPayload();
    payload['summary'] = 'x'.repeat(201);
    const dto = readAs(CreateRoomTypeDto, payload);
    expect((await errorsOn(dto, 'summary')).length).toBeGreaterThan(0);
  });

  it("entity_schema/stayDb/RoomType/summary/accepts_at_max_length", async () => {
    const payload = buildValidPayload();
    const value = 'x'.repeat(200);
    payload['summary'] = value;
    const dto = readAs(CreateRoomTypeDto, payload);
    expect(await errorsOn(dto, 'summary')).toHaveLength(0);
    expect(String((dto as Record<string, unknown>)['summary']).length).toBe(value.length);
  });

  it("entity_schema/stayDb/RoomType/createdAt/server_managed_excluded_from_create", () => {
    expect(declaredProperties(CreateRoomTypeDto)).not.toContain('createdAt');
  });

  it("entity_schema/stayDb/RoomType/createdAt/server_managed_excluded_from_update", () => {
    expect(declaredProperties(UpdateRoomTypeDto)).not.toContain('createdAt');
  });

  it("entity_schema/stayDb/RoomType/createdAt/server_managed_in_response", () => {
    expect(declaredProperties(RoomTypeResponseDto)).toContain('createdAt');
  });

  it("entity_schema/stayDb/RoomType/updatedAt/server_managed_excluded_from_create", () => {
    expect(declaredProperties(CreateRoomTypeDto)).not.toContain('updatedAt');
  });

  it("entity_schema/stayDb/RoomType/updatedAt/server_managed_excluded_from_update", () => {
    expect(declaredProperties(UpdateRoomTypeDto)).not.toContain('updatedAt');
  });

  it("entity_schema/stayDb/RoomType/updatedAt/server_managed_in_response", () => {
    expect(declaredProperties(RoomTypeResponseDto)).toContain('updatedAt');
  });

  it("entity_schema/stayDb/RoomType/id/server_managed_excluded_from_create", () => {
    expect(declaredProperties(CreateRoomTypeDto)).not.toContain('id');
  });

  it("entity_schema/stayDb/RoomType/id/server_managed_excluded_from_update", () => {
    expect(declaredProperties(UpdateRoomTypeDto)).not.toContain('id');
  });

  it("entity_schema/stayDb/RoomType/id/server_managed_in_response", () => {
    expect(declaredProperties(RoomTypeResponseDto)).toContain('id');
  });

  it("entity_schema/stayDb/RoomType/listed/default_applied", () => {
    const payload = buildRequiredPayload();
    delete payload['listed'];
    const dto = readAs(CreateRoomTypeDto, payload);
    expect((dto as Record<string, unknown>)['listed']).toEqual(true);
  });

});

describe('UpdateRoomTypeDto', () => {
  it("entity_schema/stayDb/RoomType/update_all_optional", async () => {
    const dto = readAs(UpdateRoomTypeDto, {});
    expect(await validate(dto)).toHaveLength(0);
    expect((dto as Record<string, unknown>)['name']).toBeUndefined();
    expect((dto as Record<string, unknown>)['summary']).toBeUndefined();
    expect((dto as Record<string, unknown>)['description']).toBeUndefined();
    expect((dto as Record<string, unknown>)['sleeps']).toBeUndefined();
    expect((dto as Record<string, unknown>)['nightlyRate']).toBeUndefined();
    expect((dto as Record<string, unknown>)['inventory']).toBeUndefined();
    expect((dto as Record<string, unknown>)['listed']).toBeUndefined();
  });

  it("entity_schema/stayDb/RoomType/partial_update", async () => {
    const value = `alt_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`;
    const dto = readAs(UpdateRoomTypeDto, { name: value });
    expect(await errorsOn(dto, 'name')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['name']).toEqual(value);
  });
});

describe('RoomTypeResponseDto', () => {
  it("entity_schema/stayDb/RoomType/response_from_attributes", () => {
    const source = buildValidPayload();
    const response = readAs(RoomTypeResponseDto, source) as Record<string, unknown>;
    expect(response['name']).toEqual(source['name']);
    expect(response['summary']).toEqual(source['summary']);
    expect(response['description']).toEqual(source['description']);
    expect(response['sleeps']).toEqual(source['sleeps']);
    expect(response['nightlyRate']).toEqual(source['nightlyRate']);
    expect(response['inventory']).toEqual(source['inventory']);
    expect(response['listed']).toEqual(source['listed']);
  });
});
