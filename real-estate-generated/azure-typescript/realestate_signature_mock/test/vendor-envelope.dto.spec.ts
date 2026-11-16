import { validate, ValidationError } from 'class-validator';
import { plainToInstance } from 'class-transformer';
import { CreateVendorEnvelopeDto } from '../src/dto/create-vendor-envelope.dto';
import { UpdateVendorEnvelopeDto } from '../src/dto/update-vendor-envelope.dto';
import { VendorEnvelopeResponseDto } from '../src/dto/vendor-envelope-response.dto';
import { EnvelopeStatus } from '../src/enums/envelope-status.enum';

type DtoClass = abstract new (...args: never[]) => object;

/** A request body carrying every create field. */
function buildValidPayload(): Record<string, unknown> {
  return {
    signerName: 'hello',
    documentTitle: 'foo_bar',
    status: EnvelopeStatus.Sent,
    settledAt: new Date('2025-07-22T14:00:00Z'),
    documentBody: 'Lorem ipsum dolor sit amet',
    signerEmail: 'user@example.com',
    envelopeId: `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`,
    idempotencyKey: `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`,
  };
}

/** A request body carrying only the create fields the input requires. */
function buildRequiredPayload(): Record<string, unknown> {
  return {
    signerName: 'hello',
    documentTitle: 'foo_bar',
    documentBody: 'Lorem ipsum dolor sit amet',
    signerEmail: 'user@example.com',
    envelopeId: `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`,
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

describe('CreateVendorEnvelopeDto', () => {
  it("entity_schema/signatureDb/VendorEnvelope/create_valid", async () => {
    const dto = readAs(CreateVendorEnvelopeDto, buildValidPayload());
    expect(await validate(dto)).toHaveLength(0);
  });

  it("entity_schema/signatureDb/VendorEnvelope/signerName/required", async () => {
    const payload = buildValidPayload();
    delete payload['signerName'];
    const dto = readAs(CreateVendorEnvelopeDto, payload);
    expect((await errorsOn(dto, 'signerName')).length).toBeGreaterThan(0);
  });

  it("entity_schema/signatureDb/VendorEnvelope/documentTitle/required", async () => {
    const payload = buildValidPayload();
    delete payload['documentTitle'];
    const dto = readAs(CreateVendorEnvelopeDto, payload);
    expect((await errorsOn(dto, 'documentTitle')).length).toBeGreaterThan(0);
  });

  it("entity_schema/signatureDb/VendorEnvelope/documentBody/required", async () => {
    const payload = buildValidPayload();
    delete payload['documentBody'];
    const dto = readAs(CreateVendorEnvelopeDto, payload);
    expect((await errorsOn(dto, 'documentBody')).length).toBeGreaterThan(0);
  });

  it("entity_schema/signatureDb/VendorEnvelope/signerEmail/required", async () => {
    const payload = buildValidPayload();
    delete payload['signerEmail'];
    const dto = readAs(CreateVendorEnvelopeDto, payload);
    expect((await errorsOn(dto, 'signerEmail')).length).toBeGreaterThan(0);
  });

  it("entity_schema/signatureDb/VendorEnvelope/envelopeId/required", async () => {
    const payload = buildValidPayload();
    delete payload['envelopeId'];
    const dto = readAs(CreateVendorEnvelopeDto, payload);
    expect((await errorsOn(dto, 'envelopeId')).length).toBeGreaterThan(0);
  });

  it("entity_schema/signatureDb/VendorEnvelope/idempotencyKey/required", async () => {
    const payload = buildValidPayload();
    delete payload['idempotencyKey'];
    const dto = readAs(CreateVendorEnvelopeDto, payload);
    expect((await errorsOn(dto, 'idempotencyKey')).length).toBeGreaterThan(0);
  });

  it("entity_schema/signatureDb/VendorEnvelope/signerName/rejects_over_max_length", async () => {
    const payload = buildValidPayload();
    payload['signerName'] = 'x'.repeat(201);
    const dto = readAs(CreateVendorEnvelopeDto, payload);
    expect((await errorsOn(dto, 'signerName')).length).toBeGreaterThan(0);
  });

  it("entity_schema/signatureDb/VendorEnvelope/signerName/accepts_at_max_length", async () => {
    const payload = buildValidPayload();
    const value = 'x'.repeat(200);
    payload['signerName'] = value;
    const dto = readAs(CreateVendorEnvelopeDto, payload);
    expect(await errorsOn(dto, 'signerName')).toHaveLength(0);
    expect(String((dto as Record<string, unknown>)['signerName']).length).toBe(value.length);
  });

  it("entity_schema/signatureDb/VendorEnvelope/documentTitle/rejects_over_max_length", async () => {
    const payload = buildValidPayload();
    payload['documentTitle'] = 'x'.repeat(201);
    const dto = readAs(CreateVendorEnvelopeDto, payload);
    expect((await errorsOn(dto, 'documentTitle')).length).toBeGreaterThan(0);
  });

  it("entity_schema/signatureDb/VendorEnvelope/documentTitle/accepts_at_max_length", async () => {
    const payload = buildValidPayload();
    const value = 'x'.repeat(200);
    payload['documentTitle'] = value;
    const dto = readAs(CreateVendorEnvelopeDto, payload);
    expect(await errorsOn(dto, 'documentTitle')).toHaveLength(0);
    expect(String((dto as Record<string, unknown>)['documentTitle']).length).toBe(value.length);
  });

  it("entity_schema/signatureDb/VendorEnvelope/envelopeId/rejects_over_max_length", async () => {
    const payload = buildValidPayload();
    payload['envelopeId'] = 'x'.repeat(41);
    const dto = readAs(CreateVendorEnvelopeDto, payload);
    expect((await errorsOn(dto, 'envelopeId')).length).toBeGreaterThan(0);
  });

  it("entity_schema/signatureDb/VendorEnvelope/envelopeId/accepts_at_max_length", async () => {
    const payload = buildValidPayload();
    const value = 'x'.repeat(40);
    payload['envelopeId'] = value;
    const dto = readAs(CreateVendorEnvelopeDto, payload);
    expect(await errorsOn(dto, 'envelopeId')).toHaveLength(0);
    expect(String((dto as Record<string, unknown>)['envelopeId']).length).toBe(value.length);
  });

  it("entity_schema/signatureDb/VendorEnvelope/idempotencyKey/rejects_over_max_length", async () => {
    const payload = buildValidPayload();
    payload['idempotencyKey'] = 'x'.repeat(121);
    const dto = readAs(CreateVendorEnvelopeDto, payload);
    expect((await errorsOn(dto, 'idempotencyKey')).length).toBeGreaterThan(0);
  });

  it("entity_schema/signatureDb/VendorEnvelope/idempotencyKey/accepts_at_max_length", async () => {
    const payload = buildValidPayload();
    const value = 'x'.repeat(120);
    payload['idempotencyKey'] = value;
    const dto = readAs(CreateVendorEnvelopeDto, payload);
    expect(await errorsOn(dto, 'idempotencyKey')).toHaveLength(0);
    expect(String((dto as Record<string, unknown>)['idempotencyKey']).length).toBe(value.length);
  });

  it("entity_schema/signatureDb/VendorEnvelope/createdAt/server_managed_excluded_from_create", () => {
    expect(declaredProperties(CreateVendorEnvelopeDto)).not.toContain('createdAt');
  });

  it("entity_schema/signatureDb/VendorEnvelope/createdAt/server_managed_excluded_from_update", () => {
    expect(declaredProperties(UpdateVendorEnvelopeDto)).not.toContain('createdAt');
  });

  it("entity_schema/signatureDb/VendorEnvelope/createdAt/server_managed_in_response", () => {
    expect(declaredProperties(VendorEnvelopeResponseDto)).toContain('createdAt');
  });

  it("entity_schema/signatureDb/VendorEnvelope/updatedAt/server_managed_excluded_from_create", () => {
    expect(declaredProperties(CreateVendorEnvelopeDto)).not.toContain('updatedAt');
  });

  it("entity_schema/signatureDb/VendorEnvelope/updatedAt/server_managed_excluded_from_update", () => {
    expect(declaredProperties(UpdateVendorEnvelopeDto)).not.toContain('updatedAt');
  });

  it("entity_schema/signatureDb/VendorEnvelope/updatedAt/server_managed_in_response", () => {
    expect(declaredProperties(VendorEnvelopeResponseDto)).toContain('updatedAt');
  });

  it("entity_schema/signatureDb/VendorEnvelope/id/server_managed_excluded_from_create", () => {
    expect(declaredProperties(CreateVendorEnvelopeDto)).not.toContain('id');
  });

  it("entity_schema/signatureDb/VendorEnvelope/id/server_managed_excluded_from_update", () => {
    expect(declaredProperties(UpdateVendorEnvelopeDto)).not.toContain('id');
  });

  it("entity_schema/signatureDb/VendorEnvelope/id/server_managed_in_response", () => {
    expect(declaredProperties(VendorEnvelopeResponseDto)).toContain('id');
  });

  it("entity_schema/signatureDb/VendorEnvelope/status/default_applied", () => {
    const payload = buildRequiredPayload();
    delete payload['status'];
    const dto = readAs(CreateVendorEnvelopeDto, payload);
    expect((dto as Record<string, unknown>)['status']).toEqual(EnvelopeStatus.Sent);
  });

});

describe('CreateVendorEnvelopeDto status enum', () => {
  it("entity_schema/signatureDb/VendorEnvelope/status/Sent/enum_accepts", async () => {
    const payload = buildValidPayload();
    payload['status'] = EnvelopeStatus.Sent;
    const dto = readAs(CreateVendorEnvelopeDto, payload);
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['status']).toBe(EnvelopeStatus.Sent);
  });

  it("entity_schema/signatureDb/VendorEnvelope/status/Sent/enum_coerces_string", async () => {
    const payload = buildValidPayload();
    payload['status'] = 'Sent';
    const dto = readAs(CreateVendorEnvelopeDto, payload);
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['status']).toBe(EnvelopeStatus.Sent);
  });

  it("entity_schema/signatureDb/VendorEnvelope/status/Signed/enum_accepts", async () => {
    const payload = buildValidPayload();
    payload['status'] = EnvelopeStatus.Signed;
    const dto = readAs(CreateVendorEnvelopeDto, payload);
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['status']).toBe(EnvelopeStatus.Signed);
  });

  it("entity_schema/signatureDb/VendorEnvelope/status/Signed/enum_coerces_string", async () => {
    const payload = buildValidPayload();
    payload['status'] = 'Signed';
    const dto = readAs(CreateVendorEnvelopeDto, payload);
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['status']).toBe(EnvelopeStatus.Signed);
  });

  it("entity_schema/signatureDb/VendorEnvelope/status/Declined/enum_accepts", async () => {
    const payload = buildValidPayload();
    payload['status'] = EnvelopeStatus.Declined;
    const dto = readAs(CreateVendorEnvelopeDto, payload);
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['status']).toBe(EnvelopeStatus.Declined);
  });

  it("entity_schema/signatureDb/VendorEnvelope/status/Declined/enum_coerces_string", async () => {
    const payload = buildValidPayload();
    payload['status'] = 'Declined';
    const dto = readAs(CreateVendorEnvelopeDto, payload);
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['status']).toBe(EnvelopeStatus.Declined);
  });

  it("entity_schema/signatureDb/VendorEnvelope/status/enum_rejects_invalid_string", async () => {
    const payload = buildValidPayload();
    payload['status'] = 'NotAValidMember';
    const dto = readAs(CreateVendorEnvelopeDto, payload);
    expect((await errorsOn(dto, 'status')).length).toBeGreaterThan(0);
  });

  it("entity_schema/signatureDb/VendorEnvelope/status/enum_rejects_invalid_type", async () => {
    const payload = buildValidPayload();
    payload['status'] = 42;
    const dto = readAs(CreateVendorEnvelopeDto, payload);
    expect((await errorsOn(dto, 'status')).length).toBeGreaterThan(0);
  });

  it("entity_schema/signatureDb/VendorEnvelope/status/enum_default_applied_when_omitted", () => {
    const payload = buildRequiredPayload();
    delete payload['status'];
    const dto = readAs(CreateVendorEnvelopeDto, payload);
    expect((dto as Record<string, unknown>)['status']).toEqual(EnvelopeStatus.Sent);
  });

  it("entity_schema/signatureDb/VendorEnvelope/status/enum_in_update_optional", async () => {
    const dto = readAs(UpdateVendorEnvelopeDto, {});
    expect((dto as Record<string, unknown>)['status']).toBeUndefined();
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
  });
});

describe('UpdateVendorEnvelopeDto', () => {
  it("entity_schema/signatureDb/VendorEnvelope/update_all_optional", async () => {
    const dto = readAs(UpdateVendorEnvelopeDto, {});
    expect(await validate(dto)).toHaveLength(0);
    expect((dto as Record<string, unknown>)['signerName']).toBeUndefined();
    expect((dto as Record<string, unknown>)['documentTitle']).toBeUndefined();
    expect((dto as Record<string, unknown>)['status']).toBeUndefined();
    expect((dto as Record<string, unknown>)['settledAt']).toBeUndefined();
    expect((dto as Record<string, unknown>)['documentBody']).toBeUndefined();
    expect((dto as Record<string, unknown>)['signerEmail']).toBeUndefined();
    expect((dto as Record<string, unknown>)['envelopeId']).toBeUndefined();
    expect((dto as Record<string, unknown>)['idempotencyKey']).toBeUndefined();
  });

  it("entity_schema/signatureDb/VendorEnvelope/partial_update", async () => {
    const value = 'world';
    const dto = readAs(UpdateVendorEnvelopeDto, { signerName: value });
    expect(await errorsOn(dto, 'signerName')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['signerName']).toEqual(value);
  });
});

describe('VendorEnvelopeResponseDto', () => {
  it("entity_schema/signatureDb/VendorEnvelope/response_from_attributes", () => {
    const source = buildValidPayload();
    const response = readAs(VendorEnvelopeResponseDto, source) as Record<string, unknown>;
    expect(response['signerName']).toEqual(source['signerName']);
    expect(response['documentTitle']).toEqual(source['documentTitle']);
    expect(response['status']).toEqual(source['status']);
    expect(response['settledAt']).toEqual(source['settledAt']);
    expect(response['documentBody']).toEqual(source['documentBody']);
    expect(response['signerEmail']).toEqual(source['signerEmail']);
    expect(response['envelopeId']).toEqual(source['envelopeId']);
    expect(response['idempotencyKey']).toEqual(source['idempotencyKey']);
  });

  it("entity_schema/signatureDb/VendorEnvelope/response_serializes_enum_fields", () => {
    const source: Record<string, unknown> = {
      status: EnvelopeStatus.Sent,
    };
    const response = readAs(VendorEnvelopeResponseDto, source) as Record<string, unknown>;
    expect(response['status']).toBe(EnvelopeStatus.Sent);
  });
});
