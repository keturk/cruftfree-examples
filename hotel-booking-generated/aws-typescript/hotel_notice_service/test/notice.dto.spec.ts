import { validate, ValidationError } from 'class-validator';
import { plainToInstance } from 'class-transformer';
import { CreateNoticeDto } from '../src/dto/create-notice.dto';
import { UpdateNoticeDto } from '../src/dto/update-notice.dto';
import { NoticeResponseDto } from '../src/dto/notice-response.dto';

type DtoClass = abstract new (...args: never[]) => object;

/** A request body carrying every create field. */
function buildValidPayload(): Record<string, unknown> {
  return {
    recipient: 'hello',
    subject: 'foo_bar',
    body: 'sample_text',
    delivered: true,
    attempts: 7,
    noticeKey: `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`,
  };
}

/** A request body carrying only the create fields the input requires. */
function buildRequiredPayload(): Record<string, unknown> {
  return {
    recipient: 'hello',
    subject: 'foo_bar',
    body: 'sample_text',
    noticeKey: `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`,
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

describe('CreateNoticeDto', () => {
  it("entity_schema/noticeDb/Notice/create_valid", async () => {
    const dto = readAs(CreateNoticeDto, buildValidPayload());
    expect(await validate(dto)).toHaveLength(0);
  });

  it("entity_schema/noticeDb/Notice/recipient/required", async () => {
    const payload = buildValidPayload();
    delete payload['recipient'];
    const dto = readAs(CreateNoticeDto, payload);
    expect((await errorsOn(dto, 'recipient')).length).toBeGreaterThan(0);
  });

  it("entity_schema/noticeDb/Notice/subject/required", async () => {
    const payload = buildValidPayload();
    delete payload['subject'];
    const dto = readAs(CreateNoticeDto, payload);
    expect((await errorsOn(dto, 'subject')).length).toBeGreaterThan(0);
  });

  it("entity_schema/noticeDb/Notice/body/required", async () => {
    const payload = buildValidPayload();
    delete payload['body'];
    const dto = readAs(CreateNoticeDto, payload);
    expect((await errorsOn(dto, 'body')).length).toBeGreaterThan(0);
  });

  it("entity_schema/noticeDb/Notice/noticeKey/required", async () => {
    const payload = buildValidPayload();
    delete payload['noticeKey'];
    const dto = readAs(CreateNoticeDto, payload);
    expect((await errorsOn(dto, 'noticeKey')).length).toBeGreaterThan(0);
  });

  it("entity_schema/noticeDb/Notice/recipient/rejects_over_max_length", async () => {
    const payload = buildValidPayload();
    payload['recipient'] = 'x'.repeat(201);
    const dto = readAs(CreateNoticeDto, payload);
    expect((await errorsOn(dto, 'recipient')).length).toBeGreaterThan(0);
  });

  it("entity_schema/noticeDb/Notice/recipient/accepts_at_max_length", async () => {
    const payload = buildValidPayload();
    const value = 'x'.repeat(200);
    payload['recipient'] = value;
    const dto = readAs(CreateNoticeDto, payload);
    expect(await errorsOn(dto, 'recipient')).toHaveLength(0);
    expect(String((dto as Record<string, unknown>)['recipient']).length).toBe(value.length);
  });

  it("entity_schema/noticeDb/Notice/subject/rejects_over_max_length", async () => {
    const payload = buildValidPayload();
    payload['subject'] = 'x'.repeat(201);
    const dto = readAs(CreateNoticeDto, payload);
    expect((await errorsOn(dto, 'subject')).length).toBeGreaterThan(0);
  });

  it("entity_schema/noticeDb/Notice/subject/accepts_at_max_length", async () => {
    const payload = buildValidPayload();
    const value = 'x'.repeat(200);
    payload['subject'] = value;
    const dto = readAs(CreateNoticeDto, payload);
    expect(await errorsOn(dto, 'subject')).toHaveLength(0);
    expect(String((dto as Record<string, unknown>)['subject']).length).toBe(value.length);
  });

  it("entity_schema/noticeDb/Notice/body/rejects_over_max_length", async () => {
    const payload = buildValidPayload();
    payload['body'] = 'x'.repeat(2001);
    const dto = readAs(CreateNoticeDto, payload);
    expect((await errorsOn(dto, 'body')).length).toBeGreaterThan(0);
  });

  it("entity_schema/noticeDb/Notice/body/accepts_at_max_length", async () => {
    const payload = buildValidPayload();
    const value = 'x'.repeat(2000);
    payload['body'] = value;
    const dto = readAs(CreateNoticeDto, payload);
    expect(await errorsOn(dto, 'body')).toHaveLength(0);
    expect(String((dto as Record<string, unknown>)['body']).length).toBe(value.length);
  });

  it("entity_schema/noticeDb/Notice/noticeKey/rejects_over_max_length", async () => {
    const payload = buildValidPayload();
    payload['noticeKey'] = 'x'.repeat(121);
    const dto = readAs(CreateNoticeDto, payload);
    expect((await errorsOn(dto, 'noticeKey')).length).toBeGreaterThan(0);
  });

  it("entity_schema/noticeDb/Notice/noticeKey/accepts_at_max_length", async () => {
    const payload = buildValidPayload();
    const value = 'x'.repeat(120);
    payload['noticeKey'] = value;
    const dto = readAs(CreateNoticeDto, payload);
    expect(await errorsOn(dto, 'noticeKey')).toHaveLength(0);
    expect(String((dto as Record<string, unknown>)['noticeKey']).length).toBe(value.length);
  });

  it("entity_schema/noticeDb/Notice/createdAt/server_managed_excluded_from_create", () => {
    expect(declaredProperties(CreateNoticeDto)).not.toContain('createdAt');
  });

  it("entity_schema/noticeDb/Notice/createdAt/server_managed_excluded_from_update", () => {
    expect(declaredProperties(UpdateNoticeDto)).not.toContain('createdAt');
  });

  it("entity_schema/noticeDb/Notice/createdAt/server_managed_in_response", () => {
    expect(declaredProperties(NoticeResponseDto)).toContain('createdAt');
  });

  it("entity_schema/noticeDb/Notice/updatedAt/server_managed_excluded_from_create", () => {
    expect(declaredProperties(CreateNoticeDto)).not.toContain('updatedAt');
  });

  it("entity_schema/noticeDb/Notice/updatedAt/server_managed_excluded_from_update", () => {
    expect(declaredProperties(UpdateNoticeDto)).not.toContain('updatedAt');
  });

  it("entity_schema/noticeDb/Notice/updatedAt/server_managed_in_response", () => {
    expect(declaredProperties(NoticeResponseDto)).toContain('updatedAt');
  });

  it("entity_schema/noticeDb/Notice/id/server_managed_excluded_from_create", () => {
    expect(declaredProperties(CreateNoticeDto)).not.toContain('id');
  });

  it("entity_schema/noticeDb/Notice/id/server_managed_excluded_from_update", () => {
    expect(declaredProperties(UpdateNoticeDto)).not.toContain('id');
  });

  it("entity_schema/noticeDb/Notice/id/server_managed_in_response", () => {
    expect(declaredProperties(NoticeResponseDto)).toContain('id');
  });

  it("entity_schema/noticeDb/Notice/delivered/default_applied", () => {
    const payload = buildRequiredPayload();
    delete payload['delivered'];
    const dto = readAs(CreateNoticeDto, payload);
    expect((dto as Record<string, unknown>)['delivered']).toEqual(false);
  });

  it("entity_schema/noticeDb/Notice/attempts/default_applied", () => {
    const payload = buildRequiredPayload();
    delete payload['attempts'];
    const dto = readAs(CreateNoticeDto, payload);
    expect((dto as Record<string, unknown>)['attempts']).toEqual(0);
  });

});

describe('UpdateNoticeDto', () => {
  it("entity_schema/noticeDb/Notice/update_all_optional", async () => {
    const dto = readAs(UpdateNoticeDto, {});
    expect(await validate(dto)).toHaveLength(0);
    expect((dto as Record<string, unknown>)['recipient']).toBeUndefined();
    expect((dto as Record<string, unknown>)['subject']).toBeUndefined();
    expect((dto as Record<string, unknown>)['body']).toBeUndefined();
    expect((dto as Record<string, unknown>)['delivered']).toBeUndefined();
    expect((dto as Record<string, unknown>)['attempts']).toBeUndefined();
    expect((dto as Record<string, unknown>)['noticeKey']).toBeUndefined();
  });

  it("entity_schema/noticeDb/Notice/partial_update", async () => {
    const value = 'world';
    const dto = readAs(UpdateNoticeDto, { recipient: value });
    expect(await errorsOn(dto, 'recipient')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['recipient']).toEqual(value);
  });
});

describe('NoticeResponseDto', () => {
  it("entity_schema/noticeDb/Notice/response_from_attributes", () => {
    const source = buildValidPayload();
    const response = readAs(NoticeResponseDto, source) as Record<string, unknown>;
    expect(response['recipient']).toEqual(source['recipient']);
    expect(response['subject']).toEqual(source['subject']);
    expect(response['body']).toEqual(source['body']);
    expect(response['delivered']).toEqual(source['delivered']);
    expect(response['attempts']).toEqual(source['attempts']);
    expect(response['noticeKey']).toEqual(source['noticeKey']);
  });
});
