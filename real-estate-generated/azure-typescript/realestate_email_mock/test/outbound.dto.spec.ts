import { validate, ValidationError } from 'class-validator';
import { plainToInstance } from 'class-transformer';
import { CreateOutboundDto } from '../src/dto/create-outbound.dto';
import { UpdateOutboundDto } from '../src/dto/update-outbound.dto';
import { OutboundResponseDto } from '../src/dto/outbound-response.dto';
import { DeliveryStatus } from '../src/enums/delivery-status.enum';

type DtoClass = abstract new (...args: never[]) => object;

/** A request body carrying every create field. */
function buildValidPayload(): Record<string, unknown> {
  return {
    recipient: 'sample_text',
    subject: 'test_string',
    body: 'hello',
    status: DeliveryStatus.Delivered,
    deliveryId: `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`,
    idempotencyKey: `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`,
  };
}

/** A request body carrying only the create fields the input requires. */
function buildRequiredPayload(): Record<string, unknown> {
  return {
    recipient: 'sample_text',
    subject: 'test_string',
    body: 'hello',
    status: DeliveryStatus.Delivered,
    deliveryId: `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`,
    idempotencyKey: `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`,
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

describe('CreateOutboundDto', () => {
  it("entity_schema/emailDb/Outbound/create_valid", async () => {
    const dto = readAs(CreateOutboundDto, buildValidPayload());
    expect(await validate(dto)).toHaveLength(0);
  });

  it("entity_schema/emailDb/Outbound/recipient/required", async () => {
    const payload = buildValidPayload();
    delete payload['recipient'];
    const dto = readAs(CreateOutboundDto, payload);
    expect((await errorsOn(dto, 'recipient')).length).toBeGreaterThan(0);
  });

  it("entity_schema/emailDb/Outbound/subject/required", async () => {
    const payload = buildValidPayload();
    delete payload['subject'];
    const dto = readAs(CreateOutboundDto, payload);
    expect((await errorsOn(dto, 'subject')).length).toBeGreaterThan(0);
  });

  it("entity_schema/emailDb/Outbound/body/required", async () => {
    const payload = buildValidPayload();
    delete payload['body'];
    const dto = readAs(CreateOutboundDto, payload);
    expect((await errorsOn(dto, 'body')).length).toBeGreaterThan(0);
  });

  it("entity_schema/emailDb/Outbound/status/required", async () => {
    const payload = buildValidPayload();
    delete payload['status'];
    const dto = readAs(CreateOutboundDto, payload);
    expect((await errorsOn(dto, 'status')).length).toBeGreaterThan(0);
  });

  it("entity_schema/emailDb/Outbound/deliveryId/required", async () => {
    const payload = buildValidPayload();
    delete payload['deliveryId'];
    const dto = readAs(CreateOutboundDto, payload);
    expect((await errorsOn(dto, 'deliveryId')).length).toBeGreaterThan(0);
  });

  it("entity_schema/emailDb/Outbound/idempotencyKey/required", async () => {
    const payload = buildValidPayload();
    delete payload['idempotencyKey'];
    const dto = readAs(CreateOutboundDto, payload);
    expect((await errorsOn(dto, 'idempotencyKey')).length).toBeGreaterThan(0);
  });

  it("entity_schema/emailDb/Outbound/recipient/rejects_over_max_length", async () => {
    const payload = buildValidPayload();
    payload['recipient'] = 'x'.repeat(201);
    const dto = readAs(CreateOutboundDto, payload);
    expect((await errorsOn(dto, 'recipient')).length).toBeGreaterThan(0);
  });

  it("entity_schema/emailDb/Outbound/recipient/accepts_at_max_length", async () => {
    const payload = buildValidPayload();
    const value = 'x'.repeat(200);
    payload['recipient'] = value;
    const dto = readAs(CreateOutboundDto, payload);
    expect(await errorsOn(dto, 'recipient')).toHaveLength(0);
    expect(String((dto as Record<string, unknown>)['recipient']).length).toBe(value.length);
  });

  it("entity_schema/emailDb/Outbound/subject/rejects_over_max_length", async () => {
    const payload = buildValidPayload();
    payload['subject'] = 'x'.repeat(201);
    const dto = readAs(CreateOutboundDto, payload);
    expect((await errorsOn(dto, 'subject')).length).toBeGreaterThan(0);
  });

  it("entity_schema/emailDb/Outbound/subject/accepts_at_max_length", async () => {
    const payload = buildValidPayload();
    const value = 'x'.repeat(200);
    payload['subject'] = value;
    const dto = readAs(CreateOutboundDto, payload);
    expect(await errorsOn(dto, 'subject')).toHaveLength(0);
    expect(String((dto as Record<string, unknown>)['subject']).length).toBe(value.length);
  });

  it("entity_schema/emailDb/Outbound/body/rejects_over_max_length", async () => {
    const payload = buildValidPayload();
    payload['body'] = 'x'.repeat(2001);
    const dto = readAs(CreateOutboundDto, payload);
    expect((await errorsOn(dto, 'body')).length).toBeGreaterThan(0);
  });

  it("entity_schema/emailDb/Outbound/body/accepts_at_max_length", async () => {
    const payload = buildValidPayload();
    const value = 'x'.repeat(2000);
    payload['body'] = value;
    const dto = readAs(CreateOutboundDto, payload);
    expect(await errorsOn(dto, 'body')).toHaveLength(0);
    expect(String((dto as Record<string, unknown>)['body']).length).toBe(value.length);
  });

  it("entity_schema/emailDb/Outbound/deliveryId/rejects_over_max_length", async () => {
    const payload = buildValidPayload();
    payload['deliveryId'] = 'x'.repeat(41);
    const dto = readAs(CreateOutboundDto, payload);
    expect((await errorsOn(dto, 'deliveryId')).length).toBeGreaterThan(0);
  });

  it("entity_schema/emailDb/Outbound/deliveryId/accepts_at_max_length", async () => {
    const payload = buildValidPayload();
    const value = 'x'.repeat(40);
    payload['deliveryId'] = value;
    const dto = readAs(CreateOutboundDto, payload);
    expect(await errorsOn(dto, 'deliveryId')).toHaveLength(0);
    expect(String((dto as Record<string, unknown>)['deliveryId']).length).toBe(value.length);
  });

  it("entity_schema/emailDb/Outbound/idempotencyKey/rejects_over_max_length", async () => {
    const payload = buildValidPayload();
    payload['idempotencyKey'] = 'x'.repeat(121);
    const dto = readAs(CreateOutboundDto, payload);
    expect((await errorsOn(dto, 'idempotencyKey')).length).toBeGreaterThan(0);
  });

  it("entity_schema/emailDb/Outbound/idempotencyKey/accepts_at_max_length", async () => {
    const payload = buildValidPayload();
    const value = 'x'.repeat(120);
    payload['idempotencyKey'] = value;
    const dto = readAs(CreateOutboundDto, payload);
    expect(await errorsOn(dto, 'idempotencyKey')).toHaveLength(0);
    expect(String((dto as Record<string, unknown>)['idempotencyKey']).length).toBe(value.length);
  });

  it("entity_schema/emailDb/Outbound/createdAt/server_managed_excluded_from_create", () => {
    expect(declaredProperties(CreateOutboundDto)).not.toContain('createdAt');
  });

  it("entity_schema/emailDb/Outbound/createdAt/server_managed_excluded_from_update", () => {
    expect(declaredProperties(UpdateOutboundDto)).not.toContain('createdAt');
  });

  it("entity_schema/emailDb/Outbound/createdAt/server_managed_in_response", () => {
    expect(declaredProperties(OutboundResponseDto)).toContain('createdAt');
  });

  it("entity_schema/emailDb/Outbound/updatedAt/server_managed_excluded_from_create", () => {
    expect(declaredProperties(CreateOutboundDto)).not.toContain('updatedAt');
  });

  it("entity_schema/emailDb/Outbound/updatedAt/server_managed_excluded_from_update", () => {
    expect(declaredProperties(UpdateOutboundDto)).not.toContain('updatedAt');
  });

  it("entity_schema/emailDb/Outbound/updatedAt/server_managed_in_response", () => {
    expect(declaredProperties(OutboundResponseDto)).toContain('updatedAt');
  });

  it("entity_schema/emailDb/Outbound/id/server_managed_excluded_from_create", () => {
    expect(declaredProperties(CreateOutboundDto)).not.toContain('id');
  });

  it("entity_schema/emailDb/Outbound/id/server_managed_excluded_from_update", () => {
    expect(declaredProperties(UpdateOutboundDto)).not.toContain('id');
  });

  it("entity_schema/emailDb/Outbound/id/server_managed_in_response", () => {
    expect(declaredProperties(OutboundResponseDto)).toContain('id');
  });

});

describe('CreateOutboundDto status enum', () => {
  it("entity_schema/emailDb/Outbound/status/Delivered/enum_accepts", async () => {
    const payload = buildValidPayload();
    payload['status'] = DeliveryStatus.Delivered;
    const dto = readAs(CreateOutboundDto, payload);
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['status']).toBe(DeliveryStatus.Delivered);
  });

  it("entity_schema/emailDb/Outbound/status/Delivered/enum_coerces_string", async () => {
    const payload = buildValidPayload();
    payload['status'] = 'Delivered';
    const dto = readAs(CreateOutboundDto, payload);
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['status']).toBe(DeliveryStatus.Delivered);
  });

  it("entity_schema/emailDb/Outbound/status/Bounced/enum_accepts", async () => {
    const payload = buildValidPayload();
    payload['status'] = DeliveryStatus.Bounced;
    const dto = readAs(CreateOutboundDto, payload);
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['status']).toBe(DeliveryStatus.Bounced);
  });

  it("entity_schema/emailDb/Outbound/status/Bounced/enum_coerces_string", async () => {
    const payload = buildValidPayload();
    payload['status'] = 'Bounced';
    const dto = readAs(CreateOutboundDto, payload);
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['status']).toBe(DeliveryStatus.Bounced);
  });

  it("entity_schema/emailDb/Outbound/status/enum_rejects_invalid_string", async () => {
    const payload = buildValidPayload();
    payload['status'] = 'NotAValidMember';
    const dto = readAs(CreateOutboundDto, payload);
    expect((await errorsOn(dto, 'status')).length).toBeGreaterThan(0);
  });

  it("entity_schema/emailDb/Outbound/status/enum_rejects_invalid_type", async () => {
    const payload = buildValidPayload();
    payload['status'] = 42;
    const dto = readAs(CreateOutboundDto, payload);
    expect((await errorsOn(dto, 'status')).length).toBeGreaterThan(0);
  });

  it("entity_schema/emailDb/Outbound/status/enum_in_update_optional", async () => {
    const dto = readAs(UpdateOutboundDto, {});
    expect((dto as Record<string, unknown>)['status']).toBeUndefined();
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
  });
});

describe('UpdateOutboundDto', () => {
  it("entity_schema/emailDb/Outbound/update_all_optional", async () => {
    const dto = readAs(UpdateOutboundDto, {});
    expect(await validate(dto)).toHaveLength(0);
    expect((dto as Record<string, unknown>)['recipient']).toBeUndefined();
    expect((dto as Record<string, unknown>)['subject']).toBeUndefined();
    expect((dto as Record<string, unknown>)['body']).toBeUndefined();
    expect((dto as Record<string, unknown>)['status']).toBeUndefined();
    expect((dto as Record<string, unknown>)['deliveryId']).toBeUndefined();
    expect((dto as Record<string, unknown>)['idempotencyKey']).toBeUndefined();
  });

  it("entity_schema/emailDb/Outbound/partial_update", async () => {
    const value = 'hello';
    const dto = readAs(UpdateOutboundDto, { recipient: value });
    expect(await errorsOn(dto, 'recipient')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['recipient']).toEqual(value);
  });
});

describe('OutboundResponseDto', () => {
  it("entity_schema/emailDb/Outbound/response_from_attributes", () => {
    const source = buildValidPayload();
    const response = readAs(OutboundResponseDto, source) as Record<string, unknown>;
    expect(response['recipient']).toEqual(source['recipient']);
    expect(response['subject']).toEqual(source['subject']);
    expect(response['body']).toEqual(source['body']);
    expect(response['status']).toEqual(source['status']);
    expect(response['deliveryId']).toEqual(source['deliveryId']);
    expect(response['idempotencyKey']).toEqual(source['idempotencyKey']);
  });

  it("entity_schema/emailDb/Outbound/response_serializes_enum_fields", () => {
    const source: Record<string, unknown> = {
      status: DeliveryStatus.Delivered,
    };
    const response = readAs(OutboundResponseDto, source) as Record<string, unknown>;
    expect(response['status']).toBe(DeliveryStatus.Delivered);
  });
});
