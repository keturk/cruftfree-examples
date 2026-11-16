import { validate, ValidationError } from 'class-validator';
import { plainToInstance } from 'class-transformer';
import { CreateViewingDto } from '../src/dto/create-viewing.dto';
import { UpdateViewingDto } from '../src/dto/update-viewing.dto';
import { ViewingResponseDto } from '../src/dto/viewing-response.dto';
import { ViewingStatus } from '../src/enums/viewing-status.enum';

type DtoClass = abstract new (...args: never[]) => object;

/** A request body carrying every create field. */
function buildValidPayload(): Record<string, unknown> {
  return {
    startsAt: new Date('2025-01-15T12:00:00Z'),
    endsAt: new Date('2025-03-10T16:45:00Z'),
    listingTitle: 'hello',
    buyerName: 'world',
    status: ViewingStatus.Requested,
    agentName: 'world',
    note: 'test_string',
    listingId: '550e8400-e29b-41d4-a716-446655440000',
    buyerEmail: 'admin@test.org',
    agentEmail: 'info@sample.net',
    reminderSent: false,
  };
}

/** A request body carrying only the create fields the input requires. */
function buildRequiredPayload(): Record<string, unknown> {
  return {
    startsAt: new Date('2025-01-15T12:00:00Z'),
    endsAt: new Date('2025-03-10T16:45:00Z'),
    listingTitle: 'hello',
    buyerName: 'world',
    agentName: 'world',
    listingId: '550e8400-e29b-41d4-a716-446655440000',
    buyerEmail: 'admin@test.org',
    agentEmail: 'info@sample.net',
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

describe('CreateViewingDto', () => {
  it("entity_schema/viewingDb/Viewing/create_valid", async () => {
    const dto = readAs(CreateViewingDto, buildValidPayload());
    expect(await validate(dto)).toHaveLength(0);
  });

  it("entity_schema/viewingDb/Viewing/startsAt/required", async () => {
    const payload = buildValidPayload();
    delete payload['startsAt'];
    const dto = readAs(CreateViewingDto, payload);
    expect((await errorsOn(dto, 'startsAt')).length).toBeGreaterThan(0);
  });

  it("entity_schema/viewingDb/Viewing/endsAt/required", async () => {
    const payload = buildValidPayload();
    delete payload['endsAt'];
    const dto = readAs(CreateViewingDto, payload);
    expect((await errorsOn(dto, 'endsAt')).length).toBeGreaterThan(0);
  });

  it("entity_schema/viewingDb/Viewing/listingTitle/required", async () => {
    const payload = buildValidPayload();
    delete payload['listingTitle'];
    const dto = readAs(CreateViewingDto, payload);
    expect((await errorsOn(dto, 'listingTitle')).length).toBeGreaterThan(0);
  });

  it("entity_schema/viewingDb/Viewing/buyerName/required", async () => {
    const payload = buildValidPayload();
    delete payload['buyerName'];
    const dto = readAs(CreateViewingDto, payload);
    expect((await errorsOn(dto, 'buyerName')).length).toBeGreaterThan(0);
  });

  it("entity_schema/viewingDb/Viewing/agentName/required", async () => {
    const payload = buildValidPayload();
    delete payload['agentName'];
    const dto = readAs(CreateViewingDto, payload);
    expect((await errorsOn(dto, 'agentName')).length).toBeGreaterThan(0);
  });

  it("entity_schema/viewingDb/Viewing/listingId/required", async () => {
    const payload = buildValidPayload();
    delete payload['listingId'];
    const dto = readAs(CreateViewingDto, payload);
    expect((await errorsOn(dto, 'listingId')).length).toBeGreaterThan(0);
  });

  it("entity_schema/viewingDb/Viewing/buyerEmail/required", async () => {
    const payload = buildValidPayload();
    delete payload['buyerEmail'];
    const dto = readAs(CreateViewingDto, payload);
    expect((await errorsOn(dto, 'buyerEmail')).length).toBeGreaterThan(0);
  });

  it("entity_schema/viewingDb/Viewing/agentEmail/required", async () => {
    const payload = buildValidPayload();
    delete payload['agentEmail'];
    const dto = readAs(CreateViewingDto, payload);
    expect((await errorsOn(dto, 'agentEmail')).length).toBeGreaterThan(0);
  });

  it("entity_schema/viewingDb/Viewing/listingTitle/rejects_over_max_length", async () => {
    const payload = buildValidPayload();
    payload['listingTitle'] = 'x'.repeat(201);
    const dto = readAs(CreateViewingDto, payload);
    expect((await errorsOn(dto, 'listingTitle')).length).toBeGreaterThan(0);
  });

  it("entity_schema/viewingDb/Viewing/listingTitle/accepts_at_max_length", async () => {
    const payload = buildValidPayload();
    const value = 'x'.repeat(200);
    payload['listingTitle'] = value;
    const dto = readAs(CreateViewingDto, payload);
    expect(await errorsOn(dto, 'listingTitle')).toHaveLength(0);
    expect(String((dto as Record<string, unknown>)['listingTitle']).length).toBe(value.length);
  });

  it("entity_schema/viewingDb/Viewing/buyerName/rejects_over_max_length", async () => {
    const payload = buildValidPayload();
    payload['buyerName'] = 'x'.repeat(201);
    const dto = readAs(CreateViewingDto, payload);
    expect((await errorsOn(dto, 'buyerName')).length).toBeGreaterThan(0);
  });

  it("entity_schema/viewingDb/Viewing/buyerName/accepts_at_max_length", async () => {
    const payload = buildValidPayload();
    const value = 'x'.repeat(200);
    payload['buyerName'] = value;
    const dto = readAs(CreateViewingDto, payload);
    expect(await errorsOn(dto, 'buyerName')).toHaveLength(0);
    expect(String((dto as Record<string, unknown>)['buyerName']).length).toBe(value.length);
  });

  it("entity_schema/viewingDb/Viewing/agentName/rejects_over_max_length", async () => {
    const payload = buildValidPayload();
    payload['agentName'] = 'x'.repeat(201);
    const dto = readAs(CreateViewingDto, payload);
    expect((await errorsOn(dto, 'agentName')).length).toBeGreaterThan(0);
  });

  it("entity_schema/viewingDb/Viewing/agentName/accepts_at_max_length", async () => {
    const payload = buildValidPayload();
    const value = 'x'.repeat(200);
    payload['agentName'] = value;
    const dto = readAs(CreateViewingDto, payload);
    expect(await errorsOn(dto, 'agentName')).toHaveLength(0);
    expect(String((dto as Record<string, unknown>)['agentName']).length).toBe(value.length);
  });

  it("entity_schema/viewingDb/Viewing/note/rejects_over_max_length", async () => {
    const payload = buildValidPayload();
    payload['note'] = 'x'.repeat(501);
    const dto = readAs(CreateViewingDto, payload);
    expect((await errorsOn(dto, 'note')).length).toBeGreaterThan(0);
  });

  it("entity_schema/viewingDb/Viewing/note/accepts_at_max_length", async () => {
    const payload = buildValidPayload();
    const value = 'x'.repeat(500);
    payload['note'] = value;
    const dto = readAs(CreateViewingDto, payload);
    expect(await errorsOn(dto, 'note')).toHaveLength(0);
    expect(String((dto as Record<string, unknown>)['note']).length).toBe(value.length);
  });

  it("entity_schema/viewingDb/Viewing/createdAt/server_managed_excluded_from_create", () => {
    expect(declaredProperties(CreateViewingDto)).not.toContain('createdAt');
  });

  it("entity_schema/viewingDb/Viewing/createdAt/server_managed_excluded_from_update", () => {
    expect(declaredProperties(UpdateViewingDto)).not.toContain('createdAt');
  });

  it("entity_schema/viewingDb/Viewing/createdAt/server_managed_in_response", () => {
    expect(declaredProperties(ViewingResponseDto)).toContain('createdAt');
  });

  it("entity_schema/viewingDb/Viewing/updatedAt/server_managed_excluded_from_create", () => {
    expect(declaredProperties(CreateViewingDto)).not.toContain('updatedAt');
  });

  it("entity_schema/viewingDb/Viewing/updatedAt/server_managed_excluded_from_update", () => {
    expect(declaredProperties(UpdateViewingDto)).not.toContain('updatedAt');
  });

  it("entity_schema/viewingDb/Viewing/updatedAt/server_managed_in_response", () => {
    expect(declaredProperties(ViewingResponseDto)).toContain('updatedAt');
  });

  it("entity_schema/viewingDb/Viewing/id/server_managed_excluded_from_create", () => {
    expect(declaredProperties(CreateViewingDto)).not.toContain('id');
  });

  it("entity_schema/viewingDb/Viewing/id/server_managed_excluded_from_update", () => {
    expect(declaredProperties(UpdateViewingDto)).not.toContain('id');
  });

  it("entity_schema/viewingDb/Viewing/id/server_managed_in_response", () => {
    expect(declaredProperties(ViewingResponseDto)).toContain('id');
  });

  it("entity_schema/viewingDb/Viewing/status/default_applied", () => {
    const payload = buildRequiredPayload();
    delete payload['status'];
    const dto = readAs(CreateViewingDto, payload);
    expect((dto as Record<string, unknown>)['status']).toEqual(ViewingStatus.Requested);
  });

  it("entity_schema/viewingDb/Viewing/reminderSent/default_applied", () => {
    const payload = buildRequiredPayload();
    delete payload['reminderSent'];
    const dto = readAs(CreateViewingDto, payload);
    expect((dto as Record<string, unknown>)['reminderSent']).toEqual(false);
  });

});

describe('CreateViewingDto status enum', () => {
  it("entity_schema/viewingDb/Viewing/status/Requested/enum_accepts", async () => {
    const payload = buildValidPayload();
    payload['status'] = ViewingStatus.Requested;
    const dto = readAs(CreateViewingDto, payload);
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['status']).toBe(ViewingStatus.Requested);
  });

  it("entity_schema/viewingDb/Viewing/status/Requested/enum_coerces_string", async () => {
    const payload = buildValidPayload();
    payload['status'] = 'Requested';
    const dto = readAs(CreateViewingDto, payload);
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['status']).toBe(ViewingStatus.Requested);
  });

  it("entity_schema/viewingDb/Viewing/status/Confirmed/enum_accepts", async () => {
    const payload = buildValidPayload();
    payload['status'] = ViewingStatus.Confirmed;
    const dto = readAs(CreateViewingDto, payload);
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['status']).toBe(ViewingStatus.Confirmed);
  });

  it("entity_schema/viewingDb/Viewing/status/Confirmed/enum_coerces_string", async () => {
    const payload = buildValidPayload();
    payload['status'] = 'Confirmed';
    const dto = readAs(CreateViewingDto, payload);
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['status']).toBe(ViewingStatus.Confirmed);
  });

  it("entity_schema/viewingDb/Viewing/status/Completed/enum_accepts", async () => {
    const payload = buildValidPayload();
    payload['status'] = ViewingStatus.Completed;
    const dto = readAs(CreateViewingDto, payload);
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['status']).toBe(ViewingStatus.Completed);
  });

  it("entity_schema/viewingDb/Viewing/status/Completed/enum_coerces_string", async () => {
    const payload = buildValidPayload();
    payload['status'] = 'Completed';
    const dto = readAs(CreateViewingDto, payload);
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['status']).toBe(ViewingStatus.Completed);
  });

  it("entity_schema/viewingDb/Viewing/status/Cancelled/enum_accepts", async () => {
    const payload = buildValidPayload();
    payload['status'] = ViewingStatus.Cancelled;
    const dto = readAs(CreateViewingDto, payload);
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['status']).toBe(ViewingStatus.Cancelled);
  });

  it("entity_schema/viewingDb/Viewing/status/Cancelled/enum_coerces_string", async () => {
    const payload = buildValidPayload();
    payload['status'] = 'Cancelled';
    const dto = readAs(CreateViewingDto, payload);
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['status']).toBe(ViewingStatus.Cancelled);
  });

  it("entity_schema/viewingDb/Viewing/status/NoShow/enum_accepts", async () => {
    const payload = buildValidPayload();
    payload['status'] = ViewingStatus.NoShow;
    const dto = readAs(CreateViewingDto, payload);
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['status']).toBe(ViewingStatus.NoShow);
  });

  it("entity_schema/viewingDb/Viewing/status/NoShow/enum_coerces_string", async () => {
    const payload = buildValidPayload();
    payload['status'] = 'NoShow';
    const dto = readAs(CreateViewingDto, payload);
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['status']).toBe(ViewingStatus.NoShow);
  });

  it("entity_schema/viewingDb/Viewing/status/enum_rejects_invalid_string", async () => {
    const payload = buildValidPayload();
    payload['status'] = 'NotAValidMember';
    const dto = readAs(CreateViewingDto, payload);
    expect((await errorsOn(dto, 'status')).length).toBeGreaterThan(0);
  });

  it("entity_schema/viewingDb/Viewing/status/enum_rejects_invalid_type", async () => {
    const payload = buildValidPayload();
    payload['status'] = 42;
    const dto = readAs(CreateViewingDto, payload);
    expect((await errorsOn(dto, 'status')).length).toBeGreaterThan(0);
  });

  it("entity_schema/viewingDb/Viewing/status/enum_default_applied_when_omitted", () => {
    const payload = buildRequiredPayload();
    delete payload['status'];
    const dto = readAs(CreateViewingDto, payload);
    expect((dto as Record<string, unknown>)['status']).toEqual(ViewingStatus.Requested);
  });

  it("entity_schema/viewingDb/Viewing/status/enum_in_update_optional", async () => {
    const dto = readAs(UpdateViewingDto, {});
    expect((dto as Record<string, unknown>)['status']).toBeUndefined();
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
  });
});

describe('UpdateViewingDto', () => {
  it("entity_schema/viewingDb/Viewing/update_all_optional", async () => {
    const dto = readAs(UpdateViewingDto, {});
    expect(await validate(dto)).toHaveLength(0);
    expect((dto as Record<string, unknown>)['startsAt']).toBeUndefined();
    expect((dto as Record<string, unknown>)['endsAt']).toBeUndefined();
    expect((dto as Record<string, unknown>)['listingTitle']).toBeUndefined();
    expect((dto as Record<string, unknown>)['buyerName']).toBeUndefined();
    expect((dto as Record<string, unknown>)['status']).toBeUndefined();
    expect((dto as Record<string, unknown>)['agentName']).toBeUndefined();
    expect((dto as Record<string, unknown>)['note']).toBeUndefined();
    expect((dto as Record<string, unknown>)['listingId']).toBeUndefined();
    expect((dto as Record<string, unknown>)['buyerEmail']).toBeUndefined();
    expect((dto as Record<string, unknown>)['agentEmail']).toBeUndefined();
    expect((dto as Record<string, unknown>)['reminderSent']).toBeUndefined();
  });

  it("entity_schema/viewingDb/Viewing/partial_update", async () => {
    const value = new Date('2024-06-20T08:30:00Z');
    const dto = readAs(UpdateViewingDto, { startsAt: value });
    expect(await errorsOn(dto, 'startsAt')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['startsAt']).toEqual(value);
  });
});

describe('ViewingResponseDto', () => {
  it("entity_schema/viewingDb/Viewing/response_from_attributes", () => {
    const source = buildValidPayload();
    const response = readAs(ViewingResponseDto, source) as Record<string, unknown>;
    expect(response['startsAt']).toEqual(source['startsAt']);
    expect(response['endsAt']).toEqual(source['endsAt']);
    expect(response['listingTitle']).toEqual(source['listingTitle']);
    expect(response['buyerName']).toEqual(source['buyerName']);
    expect(response['status']).toEqual(source['status']);
    expect(response['agentName']).toEqual(source['agentName']);
    expect(response['note']).toEqual(source['note']);
    expect(response['listingId']).toEqual(source['listingId']);
    expect(response['buyerEmail']).toEqual(source['buyerEmail']);
    expect(response['agentEmail']).toEqual(source['agentEmail']);
    expect(response['reminderSent']).toEqual(source['reminderSent']);
  });

  it("entity_schema/viewingDb/Viewing/response_serializes_enum_fields", () => {
    const source: Record<string, unknown> = {
      status: ViewingStatus.Requested,
    };
    const response = readAs(ViewingResponseDto, source) as Record<string, unknown>;
    expect(response['status']).toBe(ViewingStatus.Requested);
  });
});
