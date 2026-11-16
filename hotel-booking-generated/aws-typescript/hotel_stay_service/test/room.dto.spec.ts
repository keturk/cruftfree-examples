import { validate, ValidationError } from 'class-validator';
import { plainToInstance } from 'class-transformer';
import { CreateRoomDto } from '../src/dto/create-room.dto';
import { UpdateRoomDto } from '../src/dto/update-room.dto';
import { RoomResponseDto } from '../src/dto/room-response.dto';
import { RoomCondition } from '../src/enums/room-condition.enum';

type DtoClass = abstract new (...args: never[]) => object;

/** A request body carrying every create field. */
function buildValidPayload(): Record<string, unknown> {
  return {
    number: `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 3)}`,
    roomTypeId: '550e8400-e29b-41d4-a716-446655440000',
    roomTypeName: 'hello',
    floor: 42,
    condition: RoomCondition.Ready,
  };
}

/** A request body carrying only the create fields the input requires. */
function buildRequiredPayload(): Record<string, unknown> {
  return {
    number: `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 3)}`,
    roomTypeId: '550e8400-e29b-41d4-a716-446655440000',
    roomTypeName: 'hello',
    floor: 42,
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

describe('CreateRoomDto', () => {
  it("entity_schema/stayDb/Room/create_valid", async () => {
    const dto = readAs(CreateRoomDto, buildValidPayload());
    expect(await validate(dto)).toHaveLength(0);
  });

  it("entity_schema/stayDb/Room/number/required", async () => {
    const payload = buildValidPayload();
    delete payload['number'];
    const dto = readAs(CreateRoomDto, payload);
    expect((await errorsOn(dto, 'number')).length).toBeGreaterThan(0);
  });

  it("entity_schema/stayDb/Room/roomTypeId/required", async () => {
    const payload = buildValidPayload();
    delete payload['roomTypeId'];
    const dto = readAs(CreateRoomDto, payload);
    expect((await errorsOn(dto, 'roomTypeId')).length).toBeGreaterThan(0);
  });

  it("entity_schema/stayDb/Room/roomTypeName/required", async () => {
    const payload = buildValidPayload();
    delete payload['roomTypeName'];
    const dto = readAs(CreateRoomDto, payload);
    expect((await errorsOn(dto, 'roomTypeName')).length).toBeGreaterThan(0);
  });

  it("entity_schema/stayDb/Room/floor/required", async () => {
    const payload = buildValidPayload();
    delete payload['floor'];
    const dto = readAs(CreateRoomDto, payload);
    expect((await errorsOn(dto, 'floor')).length).toBeGreaterThan(0);
  });

  it("entity_schema/stayDb/Room/number/rejects_over_max_length", async () => {
    const payload = buildValidPayload();
    payload['number'] = 'x'.repeat(9);
    const dto = readAs(CreateRoomDto, payload);
    expect((await errorsOn(dto, 'number')).length).toBeGreaterThan(0);
  });

  it("entity_schema/stayDb/Room/number/accepts_at_max_length", async () => {
    const payload = buildValidPayload();
    const value = 'x'.repeat(8);
    payload['number'] = value;
    const dto = readAs(CreateRoomDto, payload);
    expect(await errorsOn(dto, 'number')).toHaveLength(0);
    expect(String((dto as Record<string, unknown>)['number']).length).toBe(value.length);
  });

  it("entity_schema/stayDb/Room/roomTypeName/rejects_over_max_length", async () => {
    const payload = buildValidPayload();
    payload['roomTypeName'] = 'x'.repeat(81);
    const dto = readAs(CreateRoomDto, payload);
    expect((await errorsOn(dto, 'roomTypeName')).length).toBeGreaterThan(0);
  });

  it("entity_schema/stayDb/Room/roomTypeName/accepts_at_max_length", async () => {
    const payload = buildValidPayload();
    const value = 'x'.repeat(80);
    payload['roomTypeName'] = value;
    const dto = readAs(CreateRoomDto, payload);
    expect(await errorsOn(dto, 'roomTypeName')).toHaveLength(0);
    expect(String((dto as Record<string, unknown>)['roomTypeName']).length).toBe(value.length);
  });

  it("entity_schema/stayDb/Room/createdAt/server_managed_excluded_from_create", () => {
    expect(declaredProperties(CreateRoomDto)).not.toContain('createdAt');
  });

  it("entity_schema/stayDb/Room/createdAt/server_managed_excluded_from_update", () => {
    expect(declaredProperties(UpdateRoomDto)).not.toContain('createdAt');
  });

  it("entity_schema/stayDb/Room/createdAt/server_managed_in_response", () => {
    expect(declaredProperties(RoomResponseDto)).toContain('createdAt');
  });

  it("entity_schema/stayDb/Room/updatedAt/server_managed_excluded_from_create", () => {
    expect(declaredProperties(CreateRoomDto)).not.toContain('updatedAt');
  });

  it("entity_schema/stayDb/Room/updatedAt/server_managed_excluded_from_update", () => {
    expect(declaredProperties(UpdateRoomDto)).not.toContain('updatedAt');
  });

  it("entity_schema/stayDb/Room/updatedAt/server_managed_in_response", () => {
    expect(declaredProperties(RoomResponseDto)).toContain('updatedAt');
  });

  it("entity_schema/stayDb/Room/id/server_managed_excluded_from_create", () => {
    expect(declaredProperties(CreateRoomDto)).not.toContain('id');
  });

  it("entity_schema/stayDb/Room/id/server_managed_excluded_from_update", () => {
    expect(declaredProperties(UpdateRoomDto)).not.toContain('id');
  });

  it("entity_schema/stayDb/Room/id/server_managed_in_response", () => {
    expect(declaredProperties(RoomResponseDto)).toContain('id');
  });

  it("entity_schema/stayDb/Room/condition/default_applied", () => {
    const payload = buildRequiredPayload();
    delete payload['condition'];
    const dto = readAs(CreateRoomDto, payload);
    expect((dto as Record<string, unknown>)['condition']).toEqual(RoomCondition.Ready);
  });

});

describe('CreateRoomDto condition enum', () => {
  it("entity_schema/stayDb/Room/condition/Ready/enum_accepts", async () => {
    const payload = buildValidPayload();
    payload['condition'] = RoomCondition.Ready;
    const dto = readAs(CreateRoomDto, payload);
    expect(await errorsOn(dto, 'condition')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['condition']).toBe(RoomCondition.Ready);
  });

  it("entity_schema/stayDb/Room/condition/Ready/enum_coerces_string", async () => {
    const payload = buildValidPayload();
    payload['condition'] = 'Ready';
    const dto = readAs(CreateRoomDto, payload);
    expect(await errorsOn(dto, 'condition')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['condition']).toBe(RoomCondition.Ready);
  });

  it("entity_schema/stayDb/Room/condition/Dirty/enum_accepts", async () => {
    const payload = buildValidPayload();
    payload['condition'] = RoomCondition.Dirty;
    const dto = readAs(CreateRoomDto, payload);
    expect(await errorsOn(dto, 'condition')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['condition']).toBe(RoomCondition.Dirty);
  });

  it("entity_schema/stayDb/Room/condition/Dirty/enum_coerces_string", async () => {
    const payload = buildValidPayload();
    payload['condition'] = 'Dirty';
    const dto = readAs(CreateRoomDto, payload);
    expect(await errorsOn(dto, 'condition')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['condition']).toBe(RoomCondition.Dirty);
  });

  it("entity_schema/stayDb/Room/condition/OutOfService/enum_accepts", async () => {
    const payload = buildValidPayload();
    payload['condition'] = RoomCondition.OutOfService;
    const dto = readAs(CreateRoomDto, payload);
    expect(await errorsOn(dto, 'condition')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['condition']).toBe(RoomCondition.OutOfService);
  });

  it("entity_schema/stayDb/Room/condition/OutOfService/enum_coerces_string", async () => {
    const payload = buildValidPayload();
    payload['condition'] = 'OutOfService';
    const dto = readAs(CreateRoomDto, payload);
    expect(await errorsOn(dto, 'condition')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['condition']).toBe(RoomCondition.OutOfService);
  });

  it("entity_schema/stayDb/Room/condition/enum_rejects_invalid_string", async () => {
    const payload = buildValidPayload();
    payload['condition'] = 'NotAValidMember';
    const dto = readAs(CreateRoomDto, payload);
    expect((await errorsOn(dto, 'condition')).length).toBeGreaterThan(0);
  });

  it("entity_schema/stayDb/Room/condition/enum_rejects_invalid_type", async () => {
    const payload = buildValidPayload();
    payload['condition'] = 42;
    const dto = readAs(CreateRoomDto, payload);
    expect((await errorsOn(dto, 'condition')).length).toBeGreaterThan(0);
  });

  it("entity_schema/stayDb/Room/condition/enum_default_applied_when_omitted", () => {
    const payload = buildRequiredPayload();
    delete payload['condition'];
    const dto = readAs(CreateRoomDto, payload);
    expect((dto as Record<string, unknown>)['condition']).toEqual(RoomCondition.Ready);
  });

  it("entity_schema/stayDb/Room/condition/enum_in_update_optional", async () => {
    const dto = readAs(UpdateRoomDto, {});
    expect((dto as Record<string, unknown>)['condition']).toBeUndefined();
    expect(await errorsOn(dto, 'condition')).toHaveLength(0);
  });
});

describe('UpdateRoomDto', () => {
  it("entity_schema/stayDb/Room/update_all_optional", async () => {
    const dto = readAs(UpdateRoomDto, {});
    expect(await validate(dto)).toHaveLength(0);
    expect((dto as Record<string, unknown>)['number']).toBeUndefined();
    expect((dto as Record<string, unknown>)['roomTypeId']).toBeUndefined();
    expect((dto as Record<string, unknown>)['roomTypeName']).toBeUndefined();
    expect((dto as Record<string, unknown>)['floor']).toBeUndefined();
    expect((dto as Record<string, unknown>)['condition']).toBeUndefined();
  });

  it("entity_schema/stayDb/Room/partial_update", async () => {
    const value = `alt_${crypto.randomUUID().replace(/-/g, '').slice(0, 4)}`;
    const dto = readAs(UpdateRoomDto, { number: value });
    expect(await errorsOn(dto, 'number')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['number']).toEqual(value);
  });
});

describe('RoomResponseDto', () => {
  it("entity_schema/stayDb/Room/response_from_attributes", () => {
    const source = buildValidPayload();
    const response = readAs(RoomResponseDto, source) as Record<string, unknown>;
    expect(response['number']).toEqual(source['number']);
    expect(response['roomTypeId']).toEqual(source['roomTypeId']);
    expect(response['roomTypeName']).toEqual(source['roomTypeName']);
    expect(response['floor']).toEqual(source['floor']);
    expect(response['condition']).toEqual(source['condition']);
  });

  it("entity_schema/stayDb/Room/response_serializes_enum_fields", () => {
    const source: Record<string, unknown> = {
      condition: RoomCondition.Ready,
    };
    const response = readAs(RoomResponseDto, source) as Record<string, unknown>;
    expect(response['condition']).toBe(RoomCondition.Ready);
  });
});
