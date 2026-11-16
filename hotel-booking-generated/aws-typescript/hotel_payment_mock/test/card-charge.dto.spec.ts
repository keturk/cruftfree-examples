import { validate, ValidationError } from 'class-validator';
import { plainToInstance } from 'class-transformer';
import { CreateCardChargeDto } from '../src/dto/create-card-charge.dto';
import { UpdateCardChargeDto } from '../src/dto/update-card-charge.dto';
import { CardChargeResponseDto } from '../src/dto/card-charge-response.dto';
import { ChargeStatus } from '../src/enums/charge-status.enum';

type DtoClass = abstract new (...args: never[]) => object;

/** A request body carrying every create field. */
function buildValidPayload(): Record<string, unknown> {
  return {
    reference: 'hello',
    amount: '19.99',
    currency: 'hel',
    status: ChargeStatus.Succeeded,
    declineReason: 'hello',
    chargeId: `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`,
    idempotencyKey: `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`,
  };
}

/** A request body carrying only the create fields the input requires. */
function buildRequiredPayload(): Record<string, unknown> {
  return {
    reference: 'hello',
    amount: '19.99',
    currency: 'hel',
    status: ChargeStatus.Succeeded,
    chargeId: `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`,
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

describe('CreateCardChargeDto', () => {
  it("entity_schema/paymentDb/CardCharge/create_valid", async () => {
    const dto = readAs(CreateCardChargeDto, buildValidPayload());
    expect(await validate(dto)).toHaveLength(0);
  });

  it("entity_schema/paymentDb/CardCharge/reference/required", async () => {
    const payload = buildValidPayload();
    delete payload['reference'];
    const dto = readAs(CreateCardChargeDto, payload);
    expect((await errorsOn(dto, 'reference')).length).toBeGreaterThan(0);
  });

  it("entity_schema/paymentDb/CardCharge/amount/required", async () => {
    const payload = buildValidPayload();
    delete payload['amount'];
    const dto = readAs(CreateCardChargeDto, payload);
    expect((await errorsOn(dto, 'amount')).length).toBeGreaterThan(0);
  });

  it("entity_schema/paymentDb/CardCharge/currency/required", async () => {
    const payload = buildValidPayload();
    delete payload['currency'];
    const dto = readAs(CreateCardChargeDto, payload);
    expect((await errorsOn(dto, 'currency')).length).toBeGreaterThan(0);
  });

  it("entity_schema/paymentDb/CardCharge/status/required", async () => {
    const payload = buildValidPayload();
    delete payload['status'];
    const dto = readAs(CreateCardChargeDto, payload);
    expect((await errorsOn(dto, 'status')).length).toBeGreaterThan(0);
  });

  it("entity_schema/paymentDb/CardCharge/chargeId/required", async () => {
    const payload = buildValidPayload();
    delete payload['chargeId'];
    const dto = readAs(CreateCardChargeDto, payload);
    expect((await errorsOn(dto, 'chargeId')).length).toBeGreaterThan(0);
  });

  it("entity_schema/paymentDb/CardCharge/idempotencyKey/required", async () => {
    const payload = buildValidPayload();
    delete payload['idempotencyKey'];
    const dto = readAs(CreateCardChargeDto, payload);
    expect((await errorsOn(dto, 'idempotencyKey')).length).toBeGreaterThan(0);
  });

  it("entity_schema/paymentDb/CardCharge/reference/rejects_over_max_length", async () => {
    const payload = buildValidPayload();
    payload['reference'] = 'x'.repeat(81);
    const dto = readAs(CreateCardChargeDto, payload);
    expect((await errorsOn(dto, 'reference')).length).toBeGreaterThan(0);
  });

  it("entity_schema/paymentDb/CardCharge/reference/accepts_at_max_length", async () => {
    const payload = buildValidPayload();
    const value = 'x'.repeat(80);
    payload['reference'] = value;
    const dto = readAs(CreateCardChargeDto, payload);
    expect(await errorsOn(dto, 'reference')).toHaveLength(0);
    expect(String((dto as Record<string, unknown>)['reference']).length).toBe(value.length);
  });

  it("entity_schema/paymentDb/CardCharge/currency/rejects_over_max_length", async () => {
    const payload = buildValidPayload();
    payload['currency'] = 'x'.repeat(4);
    const dto = readAs(CreateCardChargeDto, payload);
    expect((await errorsOn(dto, 'currency')).length).toBeGreaterThan(0);
  });

  it("entity_schema/paymentDb/CardCharge/currency/accepts_at_max_length", async () => {
    const payload = buildValidPayload();
    const value = 'x'.repeat(3);
    payload['currency'] = value;
    const dto = readAs(CreateCardChargeDto, payload);
    expect(await errorsOn(dto, 'currency')).toHaveLength(0);
    expect(String((dto as Record<string, unknown>)['currency']).length).toBe(value.length);
  });

  it("entity_schema/paymentDb/CardCharge/declineReason/rejects_over_max_length", async () => {
    const payload = buildValidPayload();
    payload['declineReason'] = 'x'.repeat(201);
    const dto = readAs(CreateCardChargeDto, payload);
    expect((await errorsOn(dto, 'declineReason')).length).toBeGreaterThan(0);
  });

  it("entity_schema/paymentDb/CardCharge/declineReason/accepts_at_max_length", async () => {
    const payload = buildValidPayload();
    const value = 'x'.repeat(200);
    payload['declineReason'] = value;
    const dto = readAs(CreateCardChargeDto, payload);
    expect(await errorsOn(dto, 'declineReason')).toHaveLength(0);
    expect(String((dto as Record<string, unknown>)['declineReason']).length).toBe(value.length);
  });

  it("entity_schema/paymentDb/CardCharge/chargeId/rejects_over_max_length", async () => {
    const payload = buildValidPayload();
    payload['chargeId'] = 'x'.repeat(41);
    const dto = readAs(CreateCardChargeDto, payload);
    expect((await errorsOn(dto, 'chargeId')).length).toBeGreaterThan(0);
  });

  it("entity_schema/paymentDb/CardCharge/chargeId/accepts_at_max_length", async () => {
    const payload = buildValidPayload();
    const value = 'x'.repeat(40);
    payload['chargeId'] = value;
    const dto = readAs(CreateCardChargeDto, payload);
    expect(await errorsOn(dto, 'chargeId')).toHaveLength(0);
    expect(String((dto as Record<string, unknown>)['chargeId']).length).toBe(value.length);
  });

  it("entity_schema/paymentDb/CardCharge/idempotencyKey/rejects_over_max_length", async () => {
    const payload = buildValidPayload();
    payload['idempotencyKey'] = 'x'.repeat(121);
    const dto = readAs(CreateCardChargeDto, payload);
    expect((await errorsOn(dto, 'idempotencyKey')).length).toBeGreaterThan(0);
  });

  it("entity_schema/paymentDb/CardCharge/idempotencyKey/accepts_at_max_length", async () => {
    const payload = buildValidPayload();
    const value = 'x'.repeat(120);
    payload['idempotencyKey'] = value;
    const dto = readAs(CreateCardChargeDto, payload);
    expect(await errorsOn(dto, 'idempotencyKey')).toHaveLength(0);
    expect(String((dto as Record<string, unknown>)['idempotencyKey']).length).toBe(value.length);
  });

  it("entity_schema/paymentDb/CardCharge/createdAt/server_managed_excluded_from_create", () => {
    expect(declaredProperties(CreateCardChargeDto)).not.toContain('createdAt');
  });

  it("entity_schema/paymentDb/CardCharge/createdAt/server_managed_excluded_from_update", () => {
    expect(declaredProperties(UpdateCardChargeDto)).not.toContain('createdAt');
  });

  it("entity_schema/paymentDb/CardCharge/createdAt/server_managed_in_response", () => {
    expect(declaredProperties(CardChargeResponseDto)).toContain('createdAt');
  });

  it("entity_schema/paymentDb/CardCharge/updatedAt/server_managed_excluded_from_create", () => {
    expect(declaredProperties(CreateCardChargeDto)).not.toContain('updatedAt');
  });

  it("entity_schema/paymentDb/CardCharge/updatedAt/server_managed_excluded_from_update", () => {
    expect(declaredProperties(UpdateCardChargeDto)).not.toContain('updatedAt');
  });

  it("entity_schema/paymentDb/CardCharge/updatedAt/server_managed_in_response", () => {
    expect(declaredProperties(CardChargeResponseDto)).toContain('updatedAt');
  });

  it("entity_schema/paymentDb/CardCharge/id/server_managed_excluded_from_create", () => {
    expect(declaredProperties(CreateCardChargeDto)).not.toContain('id');
  });

  it("entity_schema/paymentDb/CardCharge/id/server_managed_excluded_from_update", () => {
    expect(declaredProperties(UpdateCardChargeDto)).not.toContain('id');
  });

  it("entity_schema/paymentDb/CardCharge/id/server_managed_in_response", () => {
    expect(declaredProperties(CardChargeResponseDto)).toContain('id');
  });

});

describe('CreateCardChargeDto status enum', () => {
  it("entity_schema/paymentDb/CardCharge/status/Succeeded/enum_accepts", async () => {
    const payload = buildValidPayload();
    payload['status'] = ChargeStatus.Succeeded;
    const dto = readAs(CreateCardChargeDto, payload);
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['status']).toBe(ChargeStatus.Succeeded);
  });

  it("entity_schema/paymentDb/CardCharge/status/Succeeded/enum_coerces_string", async () => {
    const payload = buildValidPayload();
    payload['status'] = 'Succeeded';
    const dto = readAs(CreateCardChargeDto, payload);
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['status']).toBe(ChargeStatus.Succeeded);
  });

  it("entity_schema/paymentDb/CardCharge/status/Declined/enum_accepts", async () => {
    const payload = buildValidPayload();
    payload['status'] = ChargeStatus.Declined;
    const dto = readAs(CreateCardChargeDto, payload);
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['status']).toBe(ChargeStatus.Declined);
  });

  it("entity_schema/paymentDb/CardCharge/status/Declined/enum_coerces_string", async () => {
    const payload = buildValidPayload();
    payload['status'] = 'Declined';
    const dto = readAs(CreateCardChargeDto, payload);
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['status']).toBe(ChargeStatus.Declined);
  });

  it("entity_schema/paymentDb/CardCharge/status/Refunded/enum_accepts", async () => {
    const payload = buildValidPayload();
    payload['status'] = ChargeStatus.Refunded;
    const dto = readAs(CreateCardChargeDto, payload);
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['status']).toBe(ChargeStatus.Refunded);
  });

  it("entity_schema/paymentDb/CardCharge/status/Refunded/enum_coerces_string", async () => {
    const payload = buildValidPayload();
    payload['status'] = 'Refunded';
    const dto = readAs(CreateCardChargeDto, payload);
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['status']).toBe(ChargeStatus.Refunded);
  });

  it("entity_schema/paymentDb/CardCharge/status/enum_rejects_invalid_string", async () => {
    const payload = buildValidPayload();
    payload['status'] = 'NotAValidMember';
    const dto = readAs(CreateCardChargeDto, payload);
    expect((await errorsOn(dto, 'status')).length).toBeGreaterThan(0);
  });

  it("entity_schema/paymentDb/CardCharge/status/enum_rejects_invalid_type", async () => {
    const payload = buildValidPayload();
    payload['status'] = 42;
    const dto = readAs(CreateCardChargeDto, payload);
    expect((await errorsOn(dto, 'status')).length).toBeGreaterThan(0);
  });

  it("entity_schema/paymentDb/CardCharge/status/enum_in_update_optional", async () => {
    const dto = readAs(UpdateCardChargeDto, {});
    expect((dto as Record<string, unknown>)['status']).toBeUndefined();
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
  });
});

describe('UpdateCardChargeDto', () => {
  it("entity_schema/paymentDb/CardCharge/update_all_optional", async () => {
    const dto = readAs(UpdateCardChargeDto, {});
    expect(await validate(dto)).toHaveLength(0);
    expect((dto as Record<string, unknown>)['reference']).toBeUndefined();
    expect((dto as Record<string, unknown>)['amount']).toBeUndefined();
    expect((dto as Record<string, unknown>)['currency']).toBeUndefined();
    expect((dto as Record<string, unknown>)['status']).toBeUndefined();
    expect((dto as Record<string, unknown>)['declineReason']).toBeUndefined();
    expect((dto as Record<string, unknown>)['chargeId']).toBeUndefined();
    expect((dto as Record<string, unknown>)['idempotencyKey']).toBeUndefined();
  });

  it("entity_schema/paymentDb/CardCharge/partial_update", async () => {
    const value = 'world';
    const dto = readAs(UpdateCardChargeDto, { reference: value });
    expect(await errorsOn(dto, 'reference')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['reference']).toEqual(value);
  });
});

describe('CardChargeResponseDto', () => {
  it("entity_schema/paymentDb/CardCharge/response_from_attributes", () => {
    const source = buildValidPayload();
    const response = readAs(CardChargeResponseDto, source) as Record<string, unknown>;
    expect(response['reference']).toEqual(source['reference']);
    expect(response['amount']).toEqual(source['amount']);
    expect(response['currency']).toEqual(source['currency']);
    expect(response['status']).toEqual(source['status']);
    expect(response['declineReason']).toEqual(source['declineReason']);
    expect(response['chargeId']).toEqual(source['chargeId']);
    expect(response['idempotencyKey']).toEqual(source['idempotencyKey']);
  });

  it("entity_schema/paymentDb/CardCharge/response_serializes_enum_fields", () => {
    const source: Record<string, unknown> = {
      status: ChargeStatus.Succeeded,
    };
    const response = readAs(CardChargeResponseDto, source) as Record<string, unknown>;
    expect(response['status']).toBe(ChargeStatus.Succeeded);
  });
});
