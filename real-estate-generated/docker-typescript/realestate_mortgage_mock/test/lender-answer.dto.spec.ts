import { validate, ValidationError } from 'class-validator';
import { plainToInstance } from 'class-transformer';
import { CreateLenderAnswerDto } from '../src/dto/create-lender-answer.dto';
import { UpdateLenderAnswerDto } from '../src/dto/update-lender-answer.dto';
import { LenderAnswerResponseDto } from '../src/dto/lender-answer-response.dto';
import { PreapprovalDecision } from '../src/enums/preapproval-decision.enum';

type DtoClass = abstract new (...args: never[]) => object;

/** A request body carrying every create field. */
function buildValidPayload(): Record<string, unknown> {
  return {
    applicantName: 'foo_bar',
    amount: '9.99',
    decision: PreapprovalDecision.Approved,
    reference: `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`,
    idempotencyKey: `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`,
    applicantEmail: 'admin@test.org',
  };
}

/** A request body carrying only the create fields the input requires. */
function buildRequiredPayload(): Record<string, unknown> {
  return {
    applicantName: 'foo_bar',
    amount: '9.99',
    decision: PreapprovalDecision.Approved,
    reference: `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`,
    idempotencyKey: `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`,
    applicantEmail: 'admin@test.org',
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

describe('CreateLenderAnswerDto', () => {
  it("entity_schema/mortgageDb/LenderAnswer/create_valid", async () => {
    const dto = readAs(CreateLenderAnswerDto, buildValidPayload());
    expect(await validate(dto)).toHaveLength(0);
  });

  it("entity_schema/mortgageDb/LenderAnswer/applicantName/required", async () => {
    const payload = buildValidPayload();
    delete payload['applicantName'];
    const dto = readAs(CreateLenderAnswerDto, payload);
    expect((await errorsOn(dto, 'applicantName')).length).toBeGreaterThan(0);
  });

  it("entity_schema/mortgageDb/LenderAnswer/amount/required", async () => {
    const payload = buildValidPayload();
    delete payload['amount'];
    const dto = readAs(CreateLenderAnswerDto, payload);
    expect((await errorsOn(dto, 'amount')).length).toBeGreaterThan(0);
  });

  it("entity_schema/mortgageDb/LenderAnswer/decision/required", async () => {
    const payload = buildValidPayload();
    delete payload['decision'];
    const dto = readAs(CreateLenderAnswerDto, payload);
    expect((await errorsOn(dto, 'decision')).length).toBeGreaterThan(0);
  });

  it("entity_schema/mortgageDb/LenderAnswer/reference/required", async () => {
    const payload = buildValidPayload();
    delete payload['reference'];
    const dto = readAs(CreateLenderAnswerDto, payload);
    expect((await errorsOn(dto, 'reference')).length).toBeGreaterThan(0);
  });

  it("entity_schema/mortgageDb/LenderAnswer/idempotencyKey/required", async () => {
    const payload = buildValidPayload();
    delete payload['idempotencyKey'];
    const dto = readAs(CreateLenderAnswerDto, payload);
    expect((await errorsOn(dto, 'idempotencyKey')).length).toBeGreaterThan(0);
  });

  it("entity_schema/mortgageDb/LenderAnswer/applicantEmail/required", async () => {
    const payload = buildValidPayload();
    delete payload['applicantEmail'];
    const dto = readAs(CreateLenderAnswerDto, payload);
    expect((await errorsOn(dto, 'applicantEmail')).length).toBeGreaterThan(0);
  });

  it("entity_schema/mortgageDb/LenderAnswer/applicantName/rejects_over_max_length", async () => {
    const payload = buildValidPayload();
    payload['applicantName'] = 'x'.repeat(201);
    const dto = readAs(CreateLenderAnswerDto, payload);
    expect((await errorsOn(dto, 'applicantName')).length).toBeGreaterThan(0);
  });

  it("entity_schema/mortgageDb/LenderAnswer/applicantName/accepts_at_max_length", async () => {
    const payload = buildValidPayload();
    const value = 'x'.repeat(200);
    payload['applicantName'] = value;
    const dto = readAs(CreateLenderAnswerDto, payload);
    expect(await errorsOn(dto, 'applicantName')).toHaveLength(0);
    expect(String((dto as Record<string, unknown>)['applicantName']).length).toBe(value.length);
  });

  it("entity_schema/mortgageDb/LenderAnswer/reference/rejects_over_max_length", async () => {
    const payload = buildValidPayload();
    payload['reference'] = 'x'.repeat(41);
    const dto = readAs(CreateLenderAnswerDto, payload);
    expect((await errorsOn(dto, 'reference')).length).toBeGreaterThan(0);
  });

  it("entity_schema/mortgageDb/LenderAnswer/reference/accepts_at_max_length", async () => {
    const payload = buildValidPayload();
    const value = 'x'.repeat(40);
    payload['reference'] = value;
    const dto = readAs(CreateLenderAnswerDto, payload);
    expect(await errorsOn(dto, 'reference')).toHaveLength(0);
    expect(String((dto as Record<string, unknown>)['reference']).length).toBe(value.length);
  });

  it("entity_schema/mortgageDb/LenderAnswer/idempotencyKey/rejects_over_max_length", async () => {
    const payload = buildValidPayload();
    payload['idempotencyKey'] = 'x'.repeat(121);
    const dto = readAs(CreateLenderAnswerDto, payload);
    expect((await errorsOn(dto, 'idempotencyKey')).length).toBeGreaterThan(0);
  });

  it("entity_schema/mortgageDb/LenderAnswer/idempotencyKey/accepts_at_max_length", async () => {
    const payload = buildValidPayload();
    const value = 'x'.repeat(120);
    payload['idempotencyKey'] = value;
    const dto = readAs(CreateLenderAnswerDto, payload);
    expect(await errorsOn(dto, 'idempotencyKey')).toHaveLength(0);
    expect(String((dto as Record<string, unknown>)['idempotencyKey']).length).toBe(value.length);
  });

  it("entity_schema/mortgageDb/LenderAnswer/createdAt/server_managed_excluded_from_create", () => {
    expect(declaredProperties(CreateLenderAnswerDto)).not.toContain('createdAt');
  });

  it("entity_schema/mortgageDb/LenderAnswer/createdAt/server_managed_excluded_from_update", () => {
    expect(declaredProperties(UpdateLenderAnswerDto)).not.toContain('createdAt');
  });

  it("entity_schema/mortgageDb/LenderAnswer/createdAt/server_managed_in_response", () => {
    expect(declaredProperties(LenderAnswerResponseDto)).toContain('createdAt');
  });

  it("entity_schema/mortgageDb/LenderAnswer/updatedAt/server_managed_excluded_from_create", () => {
    expect(declaredProperties(CreateLenderAnswerDto)).not.toContain('updatedAt');
  });

  it("entity_schema/mortgageDb/LenderAnswer/updatedAt/server_managed_excluded_from_update", () => {
    expect(declaredProperties(UpdateLenderAnswerDto)).not.toContain('updatedAt');
  });

  it("entity_schema/mortgageDb/LenderAnswer/updatedAt/server_managed_in_response", () => {
    expect(declaredProperties(LenderAnswerResponseDto)).toContain('updatedAt');
  });

  it("entity_schema/mortgageDb/LenderAnswer/id/server_managed_excluded_from_create", () => {
    expect(declaredProperties(CreateLenderAnswerDto)).not.toContain('id');
  });

  it("entity_schema/mortgageDb/LenderAnswer/id/server_managed_excluded_from_update", () => {
    expect(declaredProperties(UpdateLenderAnswerDto)).not.toContain('id');
  });

  it("entity_schema/mortgageDb/LenderAnswer/id/server_managed_in_response", () => {
    expect(declaredProperties(LenderAnswerResponseDto)).toContain('id');
  });

});

describe('CreateLenderAnswerDto decision enum', () => {
  it("entity_schema/mortgageDb/LenderAnswer/decision/Approved/enum_accepts", async () => {
    const payload = buildValidPayload();
    payload['decision'] = PreapprovalDecision.Approved;
    const dto = readAs(CreateLenderAnswerDto, payload);
    expect(await errorsOn(dto, 'decision')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['decision']).toBe(PreapprovalDecision.Approved);
  });

  it("entity_schema/mortgageDb/LenderAnswer/decision/Approved/enum_coerces_string", async () => {
    const payload = buildValidPayload();
    payload['decision'] = 'Approved';
    const dto = readAs(CreateLenderAnswerDto, payload);
    expect(await errorsOn(dto, 'decision')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['decision']).toBe(PreapprovalDecision.Approved);
  });

  it("entity_schema/mortgageDb/LenderAnswer/decision/Declined/enum_accepts", async () => {
    const payload = buildValidPayload();
    payload['decision'] = PreapprovalDecision.Declined;
    const dto = readAs(CreateLenderAnswerDto, payload);
    expect(await errorsOn(dto, 'decision')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['decision']).toBe(PreapprovalDecision.Declined);
  });

  it("entity_schema/mortgageDb/LenderAnswer/decision/Declined/enum_coerces_string", async () => {
    const payload = buildValidPayload();
    payload['decision'] = 'Declined';
    const dto = readAs(CreateLenderAnswerDto, payload);
    expect(await errorsOn(dto, 'decision')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['decision']).toBe(PreapprovalDecision.Declined);
  });

  it("entity_schema/mortgageDb/LenderAnswer/decision/enum_rejects_invalid_string", async () => {
    const payload = buildValidPayload();
    payload['decision'] = 'NotAValidMember';
    const dto = readAs(CreateLenderAnswerDto, payload);
    expect((await errorsOn(dto, 'decision')).length).toBeGreaterThan(0);
  });

  it("entity_schema/mortgageDb/LenderAnswer/decision/enum_rejects_invalid_type", async () => {
    const payload = buildValidPayload();
    payload['decision'] = 42;
    const dto = readAs(CreateLenderAnswerDto, payload);
    expect((await errorsOn(dto, 'decision')).length).toBeGreaterThan(0);
  });

  it("entity_schema/mortgageDb/LenderAnswer/decision/enum_in_update_optional", async () => {
    const dto = readAs(UpdateLenderAnswerDto, {});
    expect((dto as Record<string, unknown>)['decision']).toBeUndefined();
    expect(await errorsOn(dto, 'decision')).toHaveLength(0);
  });
});

describe('UpdateLenderAnswerDto', () => {
  it("entity_schema/mortgageDb/LenderAnswer/update_all_optional", async () => {
    const dto = readAs(UpdateLenderAnswerDto, {});
    expect(await validate(dto)).toHaveLength(0);
    expect((dto as Record<string, unknown>)['applicantName']).toBeUndefined();
    expect((dto as Record<string, unknown>)['amount']).toBeUndefined();
    expect((dto as Record<string, unknown>)['decision']).toBeUndefined();
    expect((dto as Record<string, unknown>)['reference']).toBeUndefined();
    expect((dto as Record<string, unknown>)['idempotencyKey']).toBeUndefined();
    expect((dto as Record<string, unknown>)['applicantEmail']).toBeUndefined();
  });

  it("entity_schema/mortgageDb/LenderAnswer/partial_update", async () => {
    const value = 'test_string';
    const dto = readAs(UpdateLenderAnswerDto, { applicantName: value });
    expect(await errorsOn(dto, 'applicantName')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['applicantName']).toEqual(value);
  });
});

describe('LenderAnswerResponseDto', () => {
  it("entity_schema/mortgageDb/LenderAnswer/response_from_attributes", () => {
    const source = buildValidPayload();
    const response = readAs(LenderAnswerResponseDto, source) as Record<string, unknown>;
    expect(response['applicantName']).toEqual(source['applicantName']);
    expect(response['amount']).toEqual(source['amount']);
    expect(response['decision']).toEqual(source['decision']);
    expect(response['reference']).toEqual(source['reference']);
    expect(response['idempotencyKey']).toEqual(source['idempotencyKey']);
    expect(response['applicantEmail']).toEqual(source['applicantEmail']);
  });

  it("entity_schema/mortgageDb/LenderAnswer/response_serializes_enum_fields", () => {
    const source: Record<string, unknown> = {
      decision: PreapprovalDecision.Approved,
    };
    const response = readAs(LenderAnswerResponseDto, source) as Record<string, unknown>;
    expect(response['decision']).toBe(PreapprovalDecision.Approved);
  });
});
