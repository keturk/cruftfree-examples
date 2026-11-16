import { validate, ValidationError } from 'class-validator';
import { plainToInstance } from 'class-transformer';
import { CreateContractDto } from '../src/dto/create-contract.dto';
import { UpdateContractDto } from '../src/dto/update-contract.dto';
import { ContractResponseDto } from '../src/dto/contract-response.dto';
import { ContractStatus } from '../src/enums/contract-status.enum';

type DtoClass = abstract new (...args: never[]) => object;

/** A request body carrying every create field. */
function buildValidPayload(): Record<string, unknown> {
  return {
    listingTitle: 'world',
    buyerName: 'hello',
    price: '4.50',
    status: ContractStatus.AwaitingSignature,
    signedAt: new Date('2025-03-10T16:45:00Z'),
    envelopeId: 'test_string',
    listingId: '7c9e6679-7425-40de-944b-e07fc1f90ae7',
    offerId: '550e8400-e29b-41d4-a716-446655440000',
    buyerEmail: 'admin@test.org',
    agentEmail: 'hello@world.com',
  };
}

/** A request body carrying only the create fields the input requires. */
function buildRequiredPayload(): Record<string, unknown> {
  return {
    listingTitle: 'world',
    buyerName: 'hello',
    price: '4.50',
    listingId: '7c9e6679-7425-40de-944b-e07fc1f90ae7',
    offerId: '550e8400-e29b-41d4-a716-446655440000',
    buyerEmail: 'admin@test.org',
    agentEmail: 'hello@world.com',
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

describe('CreateContractDto', () => {
  it("entity_schema/dealDb/Contract/create_valid", async () => {
    const dto = readAs(CreateContractDto, buildValidPayload());
    expect(await validate(dto)).toHaveLength(0);
  });

  it("entity_schema/dealDb/Contract/listingTitle/required", async () => {
    const payload = buildValidPayload();
    delete payload['listingTitle'];
    const dto = readAs(CreateContractDto, payload);
    expect((await errorsOn(dto, 'listingTitle')).length).toBeGreaterThan(0);
  });

  it("entity_schema/dealDb/Contract/buyerName/required", async () => {
    const payload = buildValidPayload();
    delete payload['buyerName'];
    const dto = readAs(CreateContractDto, payload);
    expect((await errorsOn(dto, 'buyerName')).length).toBeGreaterThan(0);
  });

  it("entity_schema/dealDb/Contract/price/required", async () => {
    const payload = buildValidPayload();
    delete payload['price'];
    const dto = readAs(CreateContractDto, payload);
    expect((await errorsOn(dto, 'price')).length).toBeGreaterThan(0);
  });

  it("entity_schema/dealDb/Contract/listingId/required", async () => {
    const payload = buildValidPayload();
    delete payload['listingId'];
    const dto = readAs(CreateContractDto, payload);
    expect((await errorsOn(dto, 'listingId')).length).toBeGreaterThan(0);
  });

  it("entity_schema/dealDb/Contract/offerId/required", async () => {
    const payload = buildValidPayload();
    delete payload['offerId'];
    const dto = readAs(CreateContractDto, payload);
    expect((await errorsOn(dto, 'offerId')).length).toBeGreaterThan(0);
  });

  it("entity_schema/dealDb/Contract/buyerEmail/required", async () => {
    const payload = buildValidPayload();
    delete payload['buyerEmail'];
    const dto = readAs(CreateContractDto, payload);
    expect((await errorsOn(dto, 'buyerEmail')).length).toBeGreaterThan(0);
  });

  it("entity_schema/dealDb/Contract/agentEmail/required", async () => {
    const payload = buildValidPayload();
    delete payload['agentEmail'];
    const dto = readAs(CreateContractDto, payload);
    expect((await errorsOn(dto, 'agentEmail')).length).toBeGreaterThan(0);
  });

  it("entity_schema/dealDb/Contract/listingTitle/rejects_over_max_length", async () => {
    const payload = buildValidPayload();
    payload['listingTitle'] = 'x'.repeat(201);
    const dto = readAs(CreateContractDto, payload);
    expect((await errorsOn(dto, 'listingTitle')).length).toBeGreaterThan(0);
  });

  it("entity_schema/dealDb/Contract/listingTitle/accepts_at_max_length", async () => {
    const payload = buildValidPayload();
    const value = 'x'.repeat(200);
    payload['listingTitle'] = value;
    const dto = readAs(CreateContractDto, payload);
    expect(await errorsOn(dto, 'listingTitle')).toHaveLength(0);
    expect(String((dto as Record<string, unknown>)['listingTitle']).length).toBe(value.length);
  });

  it("entity_schema/dealDb/Contract/buyerName/rejects_over_max_length", async () => {
    const payload = buildValidPayload();
    payload['buyerName'] = 'x'.repeat(201);
    const dto = readAs(CreateContractDto, payload);
    expect((await errorsOn(dto, 'buyerName')).length).toBeGreaterThan(0);
  });

  it("entity_schema/dealDb/Contract/buyerName/accepts_at_max_length", async () => {
    const payload = buildValidPayload();
    const value = 'x'.repeat(200);
    payload['buyerName'] = value;
    const dto = readAs(CreateContractDto, payload);
    expect(await errorsOn(dto, 'buyerName')).toHaveLength(0);
    expect(String((dto as Record<string, unknown>)['buyerName']).length).toBe(value.length);
  });

  it("entity_schema/dealDb/Contract/envelopeId/rejects_over_max_length", async () => {
    const payload = buildValidPayload();
    payload['envelopeId'] = 'x'.repeat(41);
    const dto = readAs(CreateContractDto, payload);
    expect((await errorsOn(dto, 'envelopeId')).length).toBeGreaterThan(0);
  });

  it("entity_schema/dealDb/Contract/envelopeId/accepts_at_max_length", async () => {
    const payload = buildValidPayload();
    const value = 'x'.repeat(40);
    payload['envelopeId'] = value;
    const dto = readAs(CreateContractDto, payload);
    expect(await errorsOn(dto, 'envelopeId')).toHaveLength(0);
    expect(String((dto as Record<string, unknown>)['envelopeId']).length).toBe(value.length);
  });

  it("entity_schema/dealDb/Contract/createdAt/server_managed_excluded_from_create", () => {
    expect(declaredProperties(CreateContractDto)).not.toContain('createdAt');
  });

  it("entity_schema/dealDb/Contract/createdAt/server_managed_excluded_from_update", () => {
    expect(declaredProperties(UpdateContractDto)).not.toContain('createdAt');
  });

  it("entity_schema/dealDb/Contract/createdAt/server_managed_in_response", () => {
    expect(declaredProperties(ContractResponseDto)).toContain('createdAt');
  });

  it("entity_schema/dealDb/Contract/updatedAt/server_managed_excluded_from_create", () => {
    expect(declaredProperties(CreateContractDto)).not.toContain('updatedAt');
  });

  it("entity_schema/dealDb/Contract/updatedAt/server_managed_excluded_from_update", () => {
    expect(declaredProperties(UpdateContractDto)).not.toContain('updatedAt');
  });

  it("entity_schema/dealDb/Contract/updatedAt/server_managed_in_response", () => {
    expect(declaredProperties(ContractResponseDto)).toContain('updatedAt');
  });

  it("entity_schema/dealDb/Contract/id/server_managed_excluded_from_create", () => {
    expect(declaredProperties(CreateContractDto)).not.toContain('id');
  });

  it("entity_schema/dealDb/Contract/id/server_managed_excluded_from_update", () => {
    expect(declaredProperties(UpdateContractDto)).not.toContain('id');
  });

  it("entity_schema/dealDb/Contract/id/server_managed_in_response", () => {
    expect(declaredProperties(ContractResponseDto)).toContain('id');
  });

  it("entity_schema/dealDb/Contract/status/default_applied", () => {
    const payload = buildRequiredPayload();
    delete payload['status'];
    const dto = readAs(CreateContractDto, payload);
    expect((dto as Record<string, unknown>)['status']).toEqual(ContractStatus.AwaitingSignature);
  });

});

describe('CreateContractDto status enum', () => {
  it("entity_schema/dealDb/Contract/status/AwaitingSignature/enum_accepts", async () => {
    const payload = buildValidPayload();
    payload['status'] = ContractStatus.AwaitingSignature;
    const dto = readAs(CreateContractDto, payload);
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['status']).toBe(ContractStatus.AwaitingSignature);
  });

  it("entity_schema/dealDb/Contract/status/AwaitingSignature/enum_coerces_string", async () => {
    const payload = buildValidPayload();
    payload['status'] = 'AwaitingSignature';
    const dto = readAs(CreateContractDto, payload);
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['status']).toBe(ContractStatus.AwaitingSignature);
  });

  it("entity_schema/dealDb/Contract/status/Signed/enum_accepts", async () => {
    const payload = buildValidPayload();
    payload['status'] = ContractStatus.Signed;
    const dto = readAs(CreateContractDto, payload);
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['status']).toBe(ContractStatus.Signed);
  });

  it("entity_schema/dealDb/Contract/status/Signed/enum_coerces_string", async () => {
    const payload = buildValidPayload();
    payload['status'] = 'Signed';
    const dto = readAs(CreateContractDto, payload);
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['status']).toBe(ContractStatus.Signed);
  });

  it("entity_schema/dealDb/Contract/status/Declined/enum_accepts", async () => {
    const payload = buildValidPayload();
    payload['status'] = ContractStatus.Declined;
    const dto = readAs(CreateContractDto, payload);
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['status']).toBe(ContractStatus.Declined);
  });

  it("entity_schema/dealDb/Contract/status/Declined/enum_coerces_string", async () => {
    const payload = buildValidPayload();
    payload['status'] = 'Declined';
    const dto = readAs(CreateContractDto, payload);
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['status']).toBe(ContractStatus.Declined);
  });

  it("entity_schema/dealDb/Contract/status/enum_rejects_invalid_string", async () => {
    const payload = buildValidPayload();
    payload['status'] = 'NotAValidMember';
    const dto = readAs(CreateContractDto, payload);
    expect((await errorsOn(dto, 'status')).length).toBeGreaterThan(0);
  });

  it("entity_schema/dealDb/Contract/status/enum_rejects_invalid_type", async () => {
    const payload = buildValidPayload();
    payload['status'] = 42;
    const dto = readAs(CreateContractDto, payload);
    expect((await errorsOn(dto, 'status')).length).toBeGreaterThan(0);
  });

  it("entity_schema/dealDb/Contract/status/enum_default_applied_when_omitted", () => {
    const payload = buildRequiredPayload();
    delete payload['status'];
    const dto = readAs(CreateContractDto, payload);
    expect((dto as Record<string, unknown>)['status']).toEqual(ContractStatus.AwaitingSignature);
  });

  it("entity_schema/dealDb/Contract/status/enum_in_update_optional", async () => {
    const dto = readAs(UpdateContractDto, {});
    expect((dto as Record<string, unknown>)['status']).toBeUndefined();
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
  });
});

describe('UpdateContractDto', () => {
  it("entity_schema/dealDb/Contract/update_all_optional", async () => {
    const dto = readAs(UpdateContractDto, {});
    expect(await validate(dto)).toHaveLength(0);
    expect((dto as Record<string, unknown>)['listingTitle']).toBeUndefined();
    expect((dto as Record<string, unknown>)['buyerName']).toBeUndefined();
    expect((dto as Record<string, unknown>)['price']).toBeUndefined();
    expect((dto as Record<string, unknown>)['status']).toBeUndefined();
    expect((dto as Record<string, unknown>)['signedAt']).toBeUndefined();
    expect((dto as Record<string, unknown>)['envelopeId']).toBeUndefined();
    expect((dto as Record<string, unknown>)['listingId']).toBeUndefined();
    expect((dto as Record<string, unknown>)['offerId']).toBeUndefined();
    expect((dto as Record<string, unknown>)['buyerEmail']).toBeUndefined();
    expect((dto as Record<string, unknown>)['agentEmail']).toBeUndefined();
  });

  it("entity_schema/dealDb/Contract/partial_update", async () => {
    const value = 'foo_bar';
    const dto = readAs(UpdateContractDto, { listingTitle: value });
    expect(await errorsOn(dto, 'listingTitle')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['listingTitle']).toEqual(value);
  });
});

describe('ContractResponseDto', () => {
  it("entity_schema/dealDb/Contract/response_from_attributes", () => {
    const source = buildValidPayload();
    const response = readAs(ContractResponseDto, source) as Record<string, unknown>;
    expect(response['listingTitle']).toEqual(source['listingTitle']);
    expect(response['buyerName']).toEqual(source['buyerName']);
    expect(response['price']).toEqual(source['price']);
    expect(response['status']).toEqual(source['status']);
    expect(response['signedAt']).toEqual(source['signedAt']);
    expect(response['envelopeId']).toEqual(source['envelopeId']);
    expect(response['listingId']).toEqual(source['listingId']);
    expect(response['offerId']).toEqual(source['offerId']);
    expect(response['buyerEmail']).toEqual(source['buyerEmail']);
    expect(response['agentEmail']).toEqual(source['agentEmail']);
  });

  it("entity_schema/dealDb/Contract/response_serializes_enum_fields", () => {
    const source: Record<string, unknown> = {
      status: ContractStatus.AwaitingSignature,
    };
    const response = readAs(ContractResponseDto, source) as Record<string, unknown>;
    expect(response['status']).toBe(ContractStatus.AwaitingSignature);
  });
});
