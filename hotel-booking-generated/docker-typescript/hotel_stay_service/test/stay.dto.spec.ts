import { validate, ValidationError } from 'class-validator';
import { plainToInstance } from 'class-transformer';
import { CreateStayDto } from '../src/dto/create-stay.dto';
import { UpdateStayDto } from '../src/dto/update-stay.dto';
import { StayResponseDto } from '../src/dto/stay-response.dto';
import { StayStatus } from '../src/enums/stay-status.enum';

type DtoClass = abstract new (...args: never[]) => object;

/** A request body carrying every create field. */
function buildValidPayload(): Record<string, unknown> {
  return {
    code: `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`,
    roomTypeId: 'f47ac10b-58cc-4372-a567-0e02b2c3d479',
    roomTypeName: 'sample_text',
    roomNumber: 'sample_t',
    guestId: 'hello',
    guestName: 'sample_text',
    guestEmail: 'test@demo.io',
    arrival: '2025-07-22',
    departure: '2024-11-05',
    nights: 42,
    guests: 256,
    total: '4.50',
    status: StayStatus.Held,
    holdUntil: new Date('2025-01-15T12:00:00Z'),
    chargeId: 'hello',
    deskNote: 'Test content body with details',
  };
}

/** A request body carrying only the create fields the input requires. */
function buildRequiredPayload(): Record<string, unknown> {
  return {
    code: `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`,
    roomTypeId: 'f47ac10b-58cc-4372-a567-0e02b2c3d479',
    roomTypeName: 'sample_text',
    guestId: 'hello',
    guestName: 'sample_text',
    guestEmail: 'test@demo.io',
    arrival: '2025-07-22',
    departure: '2024-11-05',
    nights: 42,
    guests: 256,
    total: '4.50',
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

describe('CreateStayDto', () => {
  it("entity_schema/stayDb/Stay/create_valid", async () => {
    const dto = readAs(CreateStayDto, buildValidPayload());
    expect(await validate(dto)).toHaveLength(0);
  });

  it("entity_schema/stayDb/Stay/code/required", async () => {
    const payload = buildValidPayload();
    delete payload['code'];
    const dto = readAs(CreateStayDto, payload);
    expect((await errorsOn(dto, 'code')).length).toBeGreaterThan(0);
  });

  it("entity_schema/stayDb/Stay/roomTypeId/required", async () => {
    const payload = buildValidPayload();
    delete payload['roomTypeId'];
    const dto = readAs(CreateStayDto, payload);
    expect((await errorsOn(dto, 'roomTypeId')).length).toBeGreaterThan(0);
  });

  it("entity_schema/stayDb/Stay/roomTypeName/required", async () => {
    const payload = buildValidPayload();
    delete payload['roomTypeName'];
    const dto = readAs(CreateStayDto, payload);
    expect((await errorsOn(dto, 'roomTypeName')).length).toBeGreaterThan(0);
  });

  it("entity_schema/stayDb/Stay/guestId/required", async () => {
    const payload = buildValidPayload();
    delete payload['guestId'];
    const dto = readAs(CreateStayDto, payload);
    expect((await errorsOn(dto, 'guestId')).length).toBeGreaterThan(0);
  });

  it("entity_schema/stayDb/Stay/guestName/required", async () => {
    const payload = buildValidPayload();
    delete payload['guestName'];
    const dto = readAs(CreateStayDto, payload);
    expect((await errorsOn(dto, 'guestName')).length).toBeGreaterThan(0);
  });

  it("entity_schema/stayDb/Stay/guestEmail/required", async () => {
    const payload = buildValidPayload();
    delete payload['guestEmail'];
    const dto = readAs(CreateStayDto, payload);
    expect((await errorsOn(dto, 'guestEmail')).length).toBeGreaterThan(0);
  });

  it("entity_schema/stayDb/Stay/arrival/required", async () => {
    const payload = buildValidPayload();
    delete payload['arrival'];
    const dto = readAs(CreateStayDto, payload);
    expect((await errorsOn(dto, 'arrival')).length).toBeGreaterThan(0);
  });

  it("entity_schema/stayDb/Stay/departure/required", async () => {
    const payload = buildValidPayload();
    delete payload['departure'];
    const dto = readAs(CreateStayDto, payload);
    expect((await errorsOn(dto, 'departure')).length).toBeGreaterThan(0);
  });

  it("entity_schema/stayDb/Stay/nights/required", async () => {
    const payload = buildValidPayload();
    delete payload['nights'];
    const dto = readAs(CreateStayDto, payload);
    expect((await errorsOn(dto, 'nights')).length).toBeGreaterThan(0);
  });

  it("entity_schema/stayDb/Stay/guests/required", async () => {
    const payload = buildValidPayload();
    delete payload['guests'];
    const dto = readAs(CreateStayDto, payload);
    expect((await errorsOn(dto, 'guests')).length).toBeGreaterThan(0);
  });

  it("entity_schema/stayDb/Stay/total/required", async () => {
    const payload = buildValidPayload();
    delete payload['total'];
    const dto = readAs(CreateStayDto, payload);
    expect((await errorsOn(dto, 'total')).length).toBeGreaterThan(0);
  });

  it("entity_schema/stayDb/Stay/code/rejects_over_max_length", async () => {
    const payload = buildValidPayload();
    payload['code'] = 'x'.repeat(21);
    const dto = readAs(CreateStayDto, payload);
    expect((await errorsOn(dto, 'code')).length).toBeGreaterThan(0);
  });

  it("entity_schema/stayDb/Stay/code/accepts_at_max_length", async () => {
    const payload = buildValidPayload();
    const value = 'x'.repeat(20);
    payload['code'] = value;
    const dto = readAs(CreateStayDto, payload);
    expect(await errorsOn(dto, 'code')).toHaveLength(0);
    expect(String((dto as Record<string, unknown>)['code']).length).toBe(value.length);
  });

  it("entity_schema/stayDb/Stay/roomTypeName/rejects_over_max_length", async () => {
    const payload = buildValidPayload();
    payload['roomTypeName'] = 'x'.repeat(81);
    const dto = readAs(CreateStayDto, payload);
    expect((await errorsOn(dto, 'roomTypeName')).length).toBeGreaterThan(0);
  });

  it("entity_schema/stayDb/Stay/roomTypeName/accepts_at_max_length", async () => {
    const payload = buildValidPayload();
    const value = 'x'.repeat(80);
    payload['roomTypeName'] = value;
    const dto = readAs(CreateStayDto, payload);
    expect(await errorsOn(dto, 'roomTypeName')).toHaveLength(0);
    expect(String((dto as Record<string, unknown>)['roomTypeName']).length).toBe(value.length);
  });

  it("entity_schema/stayDb/Stay/roomNumber/rejects_over_max_length", async () => {
    const payload = buildValidPayload();
    payload['roomNumber'] = 'x'.repeat(9);
    const dto = readAs(CreateStayDto, payload);
    expect((await errorsOn(dto, 'roomNumber')).length).toBeGreaterThan(0);
  });

  it("entity_schema/stayDb/Stay/roomNumber/accepts_at_max_length", async () => {
    const payload = buildValidPayload();
    const value = 'x'.repeat(8);
    payload['roomNumber'] = value;
    const dto = readAs(CreateStayDto, payload);
    expect(await errorsOn(dto, 'roomNumber')).toHaveLength(0);
    expect(String((dto as Record<string, unknown>)['roomNumber']).length).toBe(value.length);
  });

  it("entity_schema/stayDb/Stay/guestId/rejects_over_max_length", async () => {
    const payload = buildValidPayload();
    payload['guestId'] = 'x'.repeat(65);
    const dto = readAs(CreateStayDto, payload);
    expect((await errorsOn(dto, 'guestId')).length).toBeGreaterThan(0);
  });

  it("entity_schema/stayDb/Stay/guestId/accepts_at_max_length", async () => {
    const payload = buildValidPayload();
    const value = 'x'.repeat(64);
    payload['guestId'] = value;
    const dto = readAs(CreateStayDto, payload);
    expect(await errorsOn(dto, 'guestId')).toHaveLength(0);
    expect(String((dto as Record<string, unknown>)['guestId']).length).toBe(value.length);
  });

  it("entity_schema/stayDb/Stay/guestName/rejects_over_max_length", async () => {
    const payload = buildValidPayload();
    payload['guestName'] = 'x'.repeat(201);
    const dto = readAs(CreateStayDto, payload);
    expect((await errorsOn(dto, 'guestName')).length).toBeGreaterThan(0);
  });

  it("entity_schema/stayDb/Stay/guestName/accepts_at_max_length", async () => {
    const payload = buildValidPayload();
    const value = 'x'.repeat(200);
    payload['guestName'] = value;
    const dto = readAs(CreateStayDto, payload);
    expect(await errorsOn(dto, 'guestName')).toHaveLength(0);
    expect(String((dto as Record<string, unknown>)['guestName']).length).toBe(value.length);
  });

  it("entity_schema/stayDb/Stay/chargeId/rejects_over_max_length", async () => {
    const payload = buildValidPayload();
    payload['chargeId'] = 'x'.repeat(41);
    const dto = readAs(CreateStayDto, payload);
    expect((await errorsOn(dto, 'chargeId')).length).toBeGreaterThan(0);
  });

  it("entity_schema/stayDb/Stay/chargeId/accepts_at_max_length", async () => {
    const payload = buildValidPayload();
    const value = 'x'.repeat(40);
    payload['chargeId'] = value;
    const dto = readAs(CreateStayDto, payload);
    expect(await errorsOn(dto, 'chargeId')).toHaveLength(0);
    expect(String((dto as Record<string, unknown>)['chargeId']).length).toBe(value.length);
  });

  it("entity_schema/stayDb/Stay/createdAt/server_managed_excluded_from_create", () => {
    expect(declaredProperties(CreateStayDto)).not.toContain('createdAt');
  });

  it("entity_schema/stayDb/Stay/createdAt/server_managed_excluded_from_update", () => {
    expect(declaredProperties(UpdateStayDto)).not.toContain('createdAt');
  });

  it("entity_schema/stayDb/Stay/createdAt/server_managed_in_response", () => {
    expect(declaredProperties(StayResponseDto)).toContain('createdAt');
  });

  it("entity_schema/stayDb/Stay/updatedAt/server_managed_excluded_from_create", () => {
    expect(declaredProperties(CreateStayDto)).not.toContain('updatedAt');
  });

  it("entity_schema/stayDb/Stay/updatedAt/server_managed_excluded_from_update", () => {
    expect(declaredProperties(UpdateStayDto)).not.toContain('updatedAt');
  });

  it("entity_schema/stayDb/Stay/updatedAt/server_managed_in_response", () => {
    expect(declaredProperties(StayResponseDto)).toContain('updatedAt');
  });

  it("entity_schema/stayDb/Stay/id/server_managed_excluded_from_create", () => {
    expect(declaredProperties(CreateStayDto)).not.toContain('id');
  });

  it("entity_schema/stayDb/Stay/id/server_managed_excluded_from_update", () => {
    expect(declaredProperties(UpdateStayDto)).not.toContain('id');
  });

  it("entity_schema/stayDb/Stay/id/server_managed_in_response", () => {
    expect(declaredProperties(StayResponseDto)).toContain('id');
  });

  it("entity_schema/stayDb/Stay/status/default_applied", () => {
    const payload = buildRequiredPayload();
    delete payload['status'];
    const dto = readAs(CreateStayDto, payload);
    expect((dto as Record<string, unknown>)['status']).toEqual(StayStatus.Held);
  });

});

describe('CreateStayDto status enum', () => {
  it("entity_schema/stayDb/Stay/status/Held/enum_accepts", async () => {
    const payload = buildValidPayload();
    payload['status'] = StayStatus.Held;
    const dto = readAs(CreateStayDto, payload);
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['status']).toBe(StayStatus.Held);
  });

  it("entity_schema/stayDb/Stay/status/Held/enum_coerces_string", async () => {
    const payload = buildValidPayload();
    payload['status'] = 'Held';
    const dto = readAs(CreateStayDto, payload);
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['status']).toBe(StayStatus.Held);
  });

  it("entity_schema/stayDb/Stay/status/Confirmed/enum_accepts", async () => {
    const payload = buildValidPayload();
    payload['status'] = StayStatus.Confirmed;
    const dto = readAs(CreateStayDto, payload);
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['status']).toBe(StayStatus.Confirmed);
  });

  it("entity_schema/stayDb/Stay/status/Confirmed/enum_coerces_string", async () => {
    const payload = buildValidPayload();
    payload['status'] = 'Confirmed';
    const dto = readAs(CreateStayDto, payload);
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['status']).toBe(StayStatus.Confirmed);
  });

  it("entity_schema/stayDb/Stay/status/CheckedIn/enum_accepts", async () => {
    const payload = buildValidPayload();
    payload['status'] = StayStatus.CheckedIn;
    const dto = readAs(CreateStayDto, payload);
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['status']).toBe(StayStatus.CheckedIn);
  });

  it("entity_schema/stayDb/Stay/status/CheckedIn/enum_coerces_string", async () => {
    const payload = buildValidPayload();
    payload['status'] = 'CheckedIn';
    const dto = readAs(CreateStayDto, payload);
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['status']).toBe(StayStatus.CheckedIn);
  });

  it("entity_schema/stayDb/Stay/status/CheckedOut/enum_accepts", async () => {
    const payload = buildValidPayload();
    payload['status'] = StayStatus.CheckedOut;
    const dto = readAs(CreateStayDto, payload);
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['status']).toBe(StayStatus.CheckedOut);
  });

  it("entity_schema/stayDb/Stay/status/CheckedOut/enum_coerces_string", async () => {
    const payload = buildValidPayload();
    payload['status'] = 'CheckedOut';
    const dto = readAs(CreateStayDto, payload);
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['status']).toBe(StayStatus.CheckedOut);
  });

  it("entity_schema/stayDb/Stay/status/Cancelled/enum_accepts", async () => {
    const payload = buildValidPayload();
    payload['status'] = StayStatus.Cancelled;
    const dto = readAs(CreateStayDto, payload);
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['status']).toBe(StayStatus.Cancelled);
  });

  it("entity_schema/stayDb/Stay/status/Cancelled/enum_coerces_string", async () => {
    const payload = buildValidPayload();
    payload['status'] = 'Cancelled';
    const dto = readAs(CreateStayDto, payload);
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['status']).toBe(StayStatus.Cancelled);
  });

  it("entity_schema/stayDb/Stay/status/Expired/enum_accepts", async () => {
    const payload = buildValidPayload();
    payload['status'] = StayStatus.Expired;
    const dto = readAs(CreateStayDto, payload);
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['status']).toBe(StayStatus.Expired);
  });

  it("entity_schema/stayDb/Stay/status/Expired/enum_coerces_string", async () => {
    const payload = buildValidPayload();
    payload['status'] = 'Expired';
    const dto = readAs(CreateStayDto, payload);
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['status']).toBe(StayStatus.Expired);
  });

  it("entity_schema/stayDb/Stay/status/enum_rejects_invalid_string", async () => {
    const payload = buildValidPayload();
    payload['status'] = 'NotAValidMember';
    const dto = readAs(CreateStayDto, payload);
    expect((await errorsOn(dto, 'status')).length).toBeGreaterThan(0);
  });

  it("entity_schema/stayDb/Stay/status/enum_rejects_invalid_type", async () => {
    const payload = buildValidPayload();
    payload['status'] = 42;
    const dto = readAs(CreateStayDto, payload);
    expect((await errorsOn(dto, 'status')).length).toBeGreaterThan(0);
  });

  it("entity_schema/stayDb/Stay/status/enum_default_applied_when_omitted", () => {
    const payload = buildRequiredPayload();
    delete payload['status'];
    const dto = readAs(CreateStayDto, payload);
    expect((dto as Record<string, unknown>)['status']).toEqual(StayStatus.Held);
  });

  it("entity_schema/stayDb/Stay/status/enum_in_update_optional", async () => {
    const dto = readAs(UpdateStayDto, {});
    expect((dto as Record<string, unknown>)['status']).toBeUndefined();
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
  });
});

describe('UpdateStayDto', () => {
  it("entity_schema/stayDb/Stay/update_all_optional", async () => {
    const dto = readAs(UpdateStayDto, {});
    expect(await validate(dto)).toHaveLength(0);
    expect((dto as Record<string, unknown>)['code']).toBeUndefined();
    expect((dto as Record<string, unknown>)['roomTypeId']).toBeUndefined();
    expect((dto as Record<string, unknown>)['roomTypeName']).toBeUndefined();
    expect((dto as Record<string, unknown>)['roomNumber']).toBeUndefined();
    expect((dto as Record<string, unknown>)['guestId']).toBeUndefined();
    expect((dto as Record<string, unknown>)['guestName']).toBeUndefined();
    expect((dto as Record<string, unknown>)['guestEmail']).toBeUndefined();
    expect((dto as Record<string, unknown>)['arrival']).toBeUndefined();
    expect((dto as Record<string, unknown>)['departure']).toBeUndefined();
    expect((dto as Record<string, unknown>)['nights']).toBeUndefined();
    expect((dto as Record<string, unknown>)['guests']).toBeUndefined();
    expect((dto as Record<string, unknown>)['total']).toBeUndefined();
    expect((dto as Record<string, unknown>)['status']).toBeUndefined();
    expect((dto as Record<string, unknown>)['holdUntil']).toBeUndefined();
    expect((dto as Record<string, unknown>)['chargeId']).toBeUndefined();
    expect((dto as Record<string, unknown>)['deskNote']).toBeUndefined();
  });

  it("entity_schema/stayDb/Stay/partial_update", async () => {
    const value = `alt_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`;
    const dto = readAs(UpdateStayDto, { code: value });
    expect(await errorsOn(dto, 'code')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['code']).toEqual(value);
  });
});

describe('StayResponseDto', () => {
  it("entity_schema/stayDb/Stay/response_from_attributes", () => {
    const source = buildValidPayload();
    const response = readAs(StayResponseDto, source) as Record<string, unknown>;
    expect(response['code']).toEqual(source['code']);
    expect(response['roomTypeId']).toEqual(source['roomTypeId']);
    expect(response['roomTypeName']).toEqual(source['roomTypeName']);
    expect(response['roomNumber']).toEqual(source['roomNumber']);
    expect(response['guestId']).toEqual(source['guestId']);
    expect(response['guestName']).toEqual(source['guestName']);
    expect(response['guestEmail']).toEqual(source['guestEmail']);
    expect(response['arrival']).toEqual(source['arrival']);
    expect(response['departure']).toEqual(source['departure']);
    expect(response['nights']).toEqual(source['nights']);
    expect(response['guests']).toEqual(source['guests']);
    expect(response['total']).toEqual(source['total']);
    expect(response['status']).toEqual(source['status']);
    expect(response['holdUntil']).toEqual(source['holdUntil']);
    expect(response['chargeId']).toEqual(source['chargeId']);
    expect(response['deskNote']).toEqual(source['deskNote']);
  });

  it("entity_schema/stayDb/Stay/response_serializes_enum_fields", () => {
    const source: Record<string, unknown> = {
      status: StayStatus.Held,
    };
    const response = readAs(StayResponseDto, source) as Record<string, unknown>;
    expect(response['status']).toBe(StayStatus.Held);
  });
});
