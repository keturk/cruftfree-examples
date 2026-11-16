import { validate, ValidationError } from 'class-validator';
import { plainToInstance } from 'class-transformer';
import { CreatePublishedNightDto } from '../src/dto/create-published-night.dto';
import { UpdatePublishedNightDto } from '../src/dto/update-published-night.dto';
import { PublishedNightResponseDto } from '../src/dto/published-night-response.dto';

type DtoClass = abstract new (...args: never[]) => object;

/** A request body carrying every create field. */
function buildValidPayload(): Record<string, unknown> {
  return {
    roomType: 'test_string',
    night: '2024-06-20',
    left: 256,
    nightlyRate: '149.00',
    receivedAt: new Date('2025-07-22T14:00:00Z'),
  };
}

/** A request body carrying only the create fields the input requires. */
function buildRequiredPayload(): Record<string, unknown> {
  return {
    roomType: 'test_string',
    night: '2024-06-20',
    left: 256,
    nightlyRate: '149.00',
    receivedAt: new Date('2025-07-22T14:00:00Z'),
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

describe('CreatePublishedNightDto', () => {
  it("entity_schema/channelDb/PublishedNight/create_valid", async () => {
    const dto = readAs(CreatePublishedNightDto, buildValidPayload());
    expect(await validate(dto)).toHaveLength(0);
  });

  it("entity_schema/channelDb/PublishedNight/roomType/required", async () => {
    const payload = buildValidPayload();
    delete payload['roomType'];
    const dto = readAs(CreatePublishedNightDto, payload);
    expect((await errorsOn(dto, 'roomType')).length).toBeGreaterThan(0);
  });

  it("entity_schema/channelDb/PublishedNight/night/required", async () => {
    const payload = buildValidPayload();
    delete payload['night'];
    const dto = readAs(CreatePublishedNightDto, payload);
    expect((await errorsOn(dto, 'night')).length).toBeGreaterThan(0);
  });

  it("entity_schema/channelDb/PublishedNight/left/required", async () => {
    const payload = buildValidPayload();
    delete payload['left'];
    const dto = readAs(CreatePublishedNightDto, payload);
    expect((await errorsOn(dto, 'left')).length).toBeGreaterThan(0);
  });

  it("entity_schema/channelDb/PublishedNight/nightlyRate/required", async () => {
    const payload = buildValidPayload();
    delete payload['nightlyRate'];
    const dto = readAs(CreatePublishedNightDto, payload);
    expect((await errorsOn(dto, 'nightlyRate')).length).toBeGreaterThan(0);
  });

  it("entity_schema/channelDb/PublishedNight/receivedAt/required", async () => {
    const payload = buildValidPayload();
    delete payload['receivedAt'];
    const dto = readAs(CreatePublishedNightDto, payload);
    expect((await errorsOn(dto, 'receivedAt')).length).toBeGreaterThan(0);
  });

  it("entity_schema/channelDb/PublishedNight/roomType/rejects_over_max_length", async () => {
    const payload = buildValidPayload();
    payload['roomType'] = 'x'.repeat(81);
    const dto = readAs(CreatePublishedNightDto, payload);
    expect((await errorsOn(dto, 'roomType')).length).toBeGreaterThan(0);
  });

  it("entity_schema/channelDb/PublishedNight/roomType/accepts_at_max_length", async () => {
    const payload = buildValidPayload();
    const value = 'x'.repeat(80);
    payload['roomType'] = value;
    const dto = readAs(CreatePublishedNightDto, payload);
    expect(await errorsOn(dto, 'roomType')).toHaveLength(0);
    expect(String((dto as Record<string, unknown>)['roomType']).length).toBe(value.length);
  });

  it("entity_schema/channelDb/PublishedNight/createdAt/server_managed_excluded_from_create", () => {
    expect(declaredProperties(CreatePublishedNightDto)).not.toContain('createdAt');
  });

  it("entity_schema/channelDb/PublishedNight/createdAt/server_managed_excluded_from_update", () => {
    expect(declaredProperties(UpdatePublishedNightDto)).not.toContain('createdAt');
  });

  it("entity_schema/channelDb/PublishedNight/createdAt/server_managed_in_response", () => {
    expect(declaredProperties(PublishedNightResponseDto)).toContain('createdAt');
  });

  it("entity_schema/channelDb/PublishedNight/updatedAt/server_managed_excluded_from_create", () => {
    expect(declaredProperties(CreatePublishedNightDto)).not.toContain('updatedAt');
  });

  it("entity_schema/channelDb/PublishedNight/updatedAt/server_managed_excluded_from_update", () => {
    expect(declaredProperties(UpdatePublishedNightDto)).not.toContain('updatedAt');
  });

  it("entity_schema/channelDb/PublishedNight/updatedAt/server_managed_in_response", () => {
    expect(declaredProperties(PublishedNightResponseDto)).toContain('updatedAt');
  });

  it("entity_schema/channelDb/PublishedNight/id/server_managed_excluded_from_create", () => {
    expect(declaredProperties(CreatePublishedNightDto)).not.toContain('id');
  });

  it("entity_schema/channelDb/PublishedNight/id/server_managed_excluded_from_update", () => {
    expect(declaredProperties(UpdatePublishedNightDto)).not.toContain('id');
  });

  it("entity_schema/channelDb/PublishedNight/id/server_managed_in_response", () => {
    expect(declaredProperties(PublishedNightResponseDto)).toContain('id');
  });

});

describe('UpdatePublishedNightDto', () => {
  it("entity_schema/channelDb/PublishedNight/update_all_optional", async () => {
    const dto = readAs(UpdatePublishedNightDto, {});
    expect(await validate(dto)).toHaveLength(0);
    expect((dto as Record<string, unknown>)['roomType']).toBeUndefined();
    expect((dto as Record<string, unknown>)['night']).toBeUndefined();
    expect((dto as Record<string, unknown>)['left']).toBeUndefined();
    expect((dto as Record<string, unknown>)['nightlyRate']).toBeUndefined();
    expect((dto as Record<string, unknown>)['receivedAt']).toBeUndefined();
  });

  it("entity_schema/channelDb/PublishedNight/partial_update", async () => {
    const value = 'sample_text';
    const dto = readAs(UpdatePublishedNightDto, { roomType: value });
    expect(await errorsOn(dto, 'roomType')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['roomType']).toEqual(value);
  });
});

describe('PublishedNightResponseDto', () => {
  it("entity_schema/channelDb/PublishedNight/response_from_attributes", () => {
    const source = buildValidPayload();
    const response = readAs(PublishedNightResponseDto, source) as Record<string, unknown>;
    expect(response['roomType']).toEqual(source['roomType']);
    expect(response['night']).toEqual(source['night']);
    expect(response['left']).toEqual(source['left']);
    expect(response['nightlyRate']).toEqual(source['nightlyRate']);
    expect(response['receivedAt']).toEqual(source['receivedAt']);
  });
});
