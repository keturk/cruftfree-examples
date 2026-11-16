import { validate, ValidationError } from 'class-validator';
import { plainToInstance } from 'class-transformer';
import { CreateOfferDto } from '../src/dto/create-offer.dto';
import { UpdateOfferDto } from '../src/dto/update-offer.dto';
import { OfferResponseDto } from '../src/dto/offer-response.dto';
import { Financing } from '../src/enums/financing.enum';
import { OfferStatus } from '../src/enums/offer-status.enum';

type DtoClass = abstract new (...args: never[]) => object;

/** A request body carrying every create field. */
function buildValidPayload(): Record<string, unknown> {
  return {
    listingTitle: 'sample_text',
    buyerName: 'hello',
    amount: '149.00',
    financing: Financing.Cash,
    status: OfferStatus.Submitted,
    lenderReference: 'sample_text',
    listingId: '7c9e6679-7425-40de-944b-e07fc1f90ae7',
    buyerEmail: 'user@example.com',
    agentEmail: 'user@example.com',
  };
}

/** A request body carrying only the create fields the input requires. */
function buildRequiredPayload(): Record<string, unknown> {
  return {
    listingTitle: 'sample_text',
    buyerName: 'hello',
    amount: '149.00',
    financing: Financing.Cash,
    listingId: '7c9e6679-7425-40de-944b-e07fc1f90ae7',
    buyerEmail: 'user@example.com',
    agentEmail: 'user@example.com',
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

describe('CreateOfferDto', () => {
  it("entity_schema/dealDb/Offer/create_valid", async () => {
    const dto = readAs(CreateOfferDto, buildValidPayload());
    expect(await validate(dto)).toHaveLength(0);
  });

  it("entity_schema/dealDb/Offer/listingTitle/required", async () => {
    const payload = buildValidPayload();
    delete payload['listingTitle'];
    const dto = readAs(CreateOfferDto, payload);
    expect((await errorsOn(dto, 'listingTitle')).length).toBeGreaterThan(0);
  });

  it("entity_schema/dealDb/Offer/buyerName/required", async () => {
    const payload = buildValidPayload();
    delete payload['buyerName'];
    const dto = readAs(CreateOfferDto, payload);
    expect((await errorsOn(dto, 'buyerName')).length).toBeGreaterThan(0);
  });

  it("entity_schema/dealDb/Offer/amount/required", async () => {
    const payload = buildValidPayload();
    delete payload['amount'];
    const dto = readAs(CreateOfferDto, payload);
    expect((await errorsOn(dto, 'amount')).length).toBeGreaterThan(0);
  });

  it("entity_schema/dealDb/Offer/financing/required", async () => {
    const payload = buildValidPayload();
    delete payload['financing'];
    const dto = readAs(CreateOfferDto, payload);
    expect((await errorsOn(dto, 'financing')).length).toBeGreaterThan(0);
  });

  it("entity_schema/dealDb/Offer/listingId/required", async () => {
    const payload = buildValidPayload();
    delete payload['listingId'];
    const dto = readAs(CreateOfferDto, payload);
    expect((await errorsOn(dto, 'listingId')).length).toBeGreaterThan(0);
  });

  it("entity_schema/dealDb/Offer/buyerEmail/required", async () => {
    const payload = buildValidPayload();
    delete payload['buyerEmail'];
    const dto = readAs(CreateOfferDto, payload);
    expect((await errorsOn(dto, 'buyerEmail')).length).toBeGreaterThan(0);
  });

  it("entity_schema/dealDb/Offer/agentEmail/required", async () => {
    const payload = buildValidPayload();
    delete payload['agentEmail'];
    const dto = readAs(CreateOfferDto, payload);
    expect((await errorsOn(dto, 'agentEmail')).length).toBeGreaterThan(0);
  });

  it("entity_schema/dealDb/Offer/listingTitle/rejects_over_max_length", async () => {
    const payload = buildValidPayload();
    payload['listingTitle'] = 'x'.repeat(201);
    const dto = readAs(CreateOfferDto, payload);
    expect((await errorsOn(dto, 'listingTitle')).length).toBeGreaterThan(0);
  });

  it("entity_schema/dealDb/Offer/listingTitle/accepts_at_max_length", async () => {
    const payload = buildValidPayload();
    const value = 'x'.repeat(200);
    payload['listingTitle'] = value;
    const dto = readAs(CreateOfferDto, payload);
    expect(await errorsOn(dto, 'listingTitle')).toHaveLength(0);
    expect(String((dto as Record<string, unknown>)['listingTitle']).length).toBe(value.length);
  });

  it("entity_schema/dealDb/Offer/buyerName/rejects_over_max_length", async () => {
    const payload = buildValidPayload();
    payload['buyerName'] = 'x'.repeat(201);
    const dto = readAs(CreateOfferDto, payload);
    expect((await errorsOn(dto, 'buyerName')).length).toBeGreaterThan(0);
  });

  it("entity_schema/dealDb/Offer/buyerName/accepts_at_max_length", async () => {
    const payload = buildValidPayload();
    const value = 'x'.repeat(200);
    payload['buyerName'] = value;
    const dto = readAs(CreateOfferDto, payload);
    expect(await errorsOn(dto, 'buyerName')).toHaveLength(0);
    expect(String((dto as Record<string, unknown>)['buyerName']).length).toBe(value.length);
  });

  it("entity_schema/dealDb/Offer/lenderReference/rejects_over_max_length", async () => {
    const payload = buildValidPayload();
    payload['lenderReference'] = 'x'.repeat(41);
    const dto = readAs(CreateOfferDto, payload);
    expect((await errorsOn(dto, 'lenderReference')).length).toBeGreaterThan(0);
  });

  it("entity_schema/dealDb/Offer/lenderReference/accepts_at_max_length", async () => {
    const payload = buildValidPayload();
    const value = 'x'.repeat(40);
    payload['lenderReference'] = value;
    const dto = readAs(CreateOfferDto, payload);
    expect(await errorsOn(dto, 'lenderReference')).toHaveLength(0);
    expect(String((dto as Record<string, unknown>)['lenderReference']).length).toBe(value.length);
  });

  it("entity_schema/dealDb/Offer/createdAt/server_managed_excluded_from_create", () => {
    expect(declaredProperties(CreateOfferDto)).not.toContain('createdAt');
  });

  it("entity_schema/dealDb/Offer/createdAt/server_managed_excluded_from_update", () => {
    expect(declaredProperties(UpdateOfferDto)).not.toContain('createdAt');
  });

  it("entity_schema/dealDb/Offer/createdAt/server_managed_in_response", () => {
    expect(declaredProperties(OfferResponseDto)).toContain('createdAt');
  });

  it("entity_schema/dealDb/Offer/updatedAt/server_managed_excluded_from_create", () => {
    expect(declaredProperties(CreateOfferDto)).not.toContain('updatedAt');
  });

  it("entity_schema/dealDb/Offer/updatedAt/server_managed_excluded_from_update", () => {
    expect(declaredProperties(UpdateOfferDto)).not.toContain('updatedAt');
  });

  it("entity_schema/dealDb/Offer/updatedAt/server_managed_in_response", () => {
    expect(declaredProperties(OfferResponseDto)).toContain('updatedAt');
  });

  it("entity_schema/dealDb/Offer/id/server_managed_excluded_from_create", () => {
    expect(declaredProperties(CreateOfferDto)).not.toContain('id');
  });

  it("entity_schema/dealDb/Offer/id/server_managed_excluded_from_update", () => {
    expect(declaredProperties(UpdateOfferDto)).not.toContain('id');
  });

  it("entity_schema/dealDb/Offer/id/server_managed_in_response", () => {
    expect(declaredProperties(OfferResponseDto)).toContain('id');
  });

  it("entity_schema/dealDb/Offer/status/default_applied", () => {
    const payload = buildRequiredPayload();
    delete payload['status'];
    const dto = readAs(CreateOfferDto, payload);
    expect((dto as Record<string, unknown>)['status']).toEqual(OfferStatus.Submitted);
  });

});

describe('CreateOfferDto financing enum', () => {
  it("entity_schema/dealDb/Offer/financing/Cash/enum_accepts", async () => {
    const payload = buildValidPayload();
    payload['financing'] = Financing.Cash;
    const dto = readAs(CreateOfferDto, payload);
    expect(await errorsOn(dto, 'financing')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['financing']).toBe(Financing.Cash);
  });

  it("entity_schema/dealDb/Offer/financing/Cash/enum_coerces_string", async () => {
    const payload = buildValidPayload();
    payload['financing'] = 'Cash';
    const dto = readAs(CreateOfferDto, payload);
    expect(await errorsOn(dto, 'financing')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['financing']).toBe(Financing.Cash);
  });

  it("entity_schema/dealDb/Offer/financing/Mortgage/enum_accepts", async () => {
    const payload = buildValidPayload();
    payload['financing'] = Financing.Mortgage;
    const dto = readAs(CreateOfferDto, payload);
    expect(await errorsOn(dto, 'financing')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['financing']).toBe(Financing.Mortgage);
  });

  it("entity_schema/dealDb/Offer/financing/Mortgage/enum_coerces_string", async () => {
    const payload = buildValidPayload();
    payload['financing'] = 'Mortgage';
    const dto = readAs(CreateOfferDto, payload);
    expect(await errorsOn(dto, 'financing')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['financing']).toBe(Financing.Mortgage);
  });

  it("entity_schema/dealDb/Offer/financing/enum_rejects_invalid_string", async () => {
    const payload = buildValidPayload();
    payload['financing'] = 'NotAValidMember';
    const dto = readAs(CreateOfferDto, payload);
    expect((await errorsOn(dto, 'financing')).length).toBeGreaterThan(0);
  });

  it("entity_schema/dealDb/Offer/financing/enum_rejects_invalid_type", async () => {
    const payload = buildValidPayload();
    payload['financing'] = 42;
    const dto = readAs(CreateOfferDto, payload);
    expect((await errorsOn(dto, 'financing')).length).toBeGreaterThan(0);
  });

  it("entity_schema/dealDb/Offer/financing/enum_in_update_optional", async () => {
    const dto = readAs(UpdateOfferDto, {});
    expect((dto as Record<string, unknown>)['financing']).toBeUndefined();
    expect(await errorsOn(dto, 'financing')).toHaveLength(0);
  });
});

describe('CreateOfferDto status enum', () => {
  it("entity_schema/dealDb/Offer/status/Submitted/enum_accepts", async () => {
    const payload = buildValidPayload();
    payload['status'] = OfferStatus.Submitted;
    const dto = readAs(CreateOfferDto, payload);
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['status']).toBe(OfferStatus.Submitted);
  });

  it("entity_schema/dealDb/Offer/status/Submitted/enum_coerces_string", async () => {
    const payload = buildValidPayload();
    payload['status'] = 'Submitted';
    const dto = readAs(CreateOfferDto, payload);
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['status']).toBe(OfferStatus.Submitted);
  });

  it("entity_schema/dealDb/Offer/status/Accepted/enum_accepts", async () => {
    const payload = buildValidPayload();
    payload['status'] = OfferStatus.Accepted;
    const dto = readAs(CreateOfferDto, payload);
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['status']).toBe(OfferStatus.Accepted);
  });

  it("entity_schema/dealDb/Offer/status/Accepted/enum_coerces_string", async () => {
    const payload = buildValidPayload();
    payload['status'] = 'Accepted';
    const dto = readAs(CreateOfferDto, payload);
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['status']).toBe(OfferStatus.Accepted);
  });

  it("entity_schema/dealDb/Offer/status/Rejected/enum_accepts", async () => {
    const payload = buildValidPayload();
    payload['status'] = OfferStatus.Rejected;
    const dto = readAs(CreateOfferDto, payload);
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['status']).toBe(OfferStatus.Rejected);
  });

  it("entity_schema/dealDb/Offer/status/Rejected/enum_coerces_string", async () => {
    const payload = buildValidPayload();
    payload['status'] = 'Rejected';
    const dto = readAs(CreateOfferDto, payload);
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['status']).toBe(OfferStatus.Rejected);
  });

  it("entity_schema/dealDb/Offer/status/Withdrawn/enum_accepts", async () => {
    const payload = buildValidPayload();
    payload['status'] = OfferStatus.Withdrawn;
    const dto = readAs(CreateOfferDto, payload);
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['status']).toBe(OfferStatus.Withdrawn);
  });

  it("entity_schema/dealDb/Offer/status/Withdrawn/enum_coerces_string", async () => {
    const payload = buildValidPayload();
    payload['status'] = 'Withdrawn';
    const dto = readAs(CreateOfferDto, payload);
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['status']).toBe(OfferStatus.Withdrawn);
  });

  it("entity_schema/dealDb/Offer/status/enum_rejects_invalid_string", async () => {
    const payload = buildValidPayload();
    payload['status'] = 'NotAValidMember';
    const dto = readAs(CreateOfferDto, payload);
    expect((await errorsOn(dto, 'status')).length).toBeGreaterThan(0);
  });

  it("entity_schema/dealDb/Offer/status/enum_rejects_invalid_type", async () => {
    const payload = buildValidPayload();
    payload['status'] = 42;
    const dto = readAs(CreateOfferDto, payload);
    expect((await errorsOn(dto, 'status')).length).toBeGreaterThan(0);
  });

  it("entity_schema/dealDb/Offer/status/enum_default_applied_when_omitted", () => {
    const payload = buildRequiredPayload();
    delete payload['status'];
    const dto = readAs(CreateOfferDto, payload);
    expect((dto as Record<string, unknown>)['status']).toEqual(OfferStatus.Submitted);
  });

  it("entity_schema/dealDb/Offer/status/enum_in_update_optional", async () => {
    const dto = readAs(UpdateOfferDto, {});
    expect((dto as Record<string, unknown>)['status']).toBeUndefined();
    expect(await errorsOn(dto, 'status')).toHaveLength(0);
  });
});

describe('UpdateOfferDto', () => {
  it("entity_schema/dealDb/Offer/update_all_optional", async () => {
    const dto = readAs(UpdateOfferDto, {});
    expect(await validate(dto)).toHaveLength(0);
    expect((dto as Record<string, unknown>)['listingTitle']).toBeUndefined();
    expect((dto as Record<string, unknown>)['buyerName']).toBeUndefined();
    expect((dto as Record<string, unknown>)['amount']).toBeUndefined();
    expect((dto as Record<string, unknown>)['financing']).toBeUndefined();
    expect((dto as Record<string, unknown>)['status']).toBeUndefined();
    expect((dto as Record<string, unknown>)['lenderReference']).toBeUndefined();
    expect((dto as Record<string, unknown>)['listingId']).toBeUndefined();
    expect((dto as Record<string, unknown>)['buyerEmail']).toBeUndefined();
    expect((dto as Record<string, unknown>)['agentEmail']).toBeUndefined();
  });

  it("entity_schema/dealDb/Offer/partial_update", async () => {
    const value = 'hello';
    const dto = readAs(UpdateOfferDto, { listingTitle: value });
    expect(await errorsOn(dto, 'listingTitle')).toHaveLength(0);
    expect((dto as Record<string, unknown>)['listingTitle']).toEqual(value);
  });
});

describe('OfferResponseDto', () => {
  it("entity_schema/dealDb/Offer/response_from_attributes", () => {
    const source = buildValidPayload();
    const response = readAs(OfferResponseDto, source) as Record<string, unknown>;
    expect(response['listingTitle']).toEqual(source['listingTitle']);
    expect(response['buyerName']).toEqual(source['buyerName']);
    expect(response['amount']).toEqual(source['amount']);
    expect(response['financing']).toEqual(source['financing']);
    expect(response['status']).toEqual(source['status']);
    expect(response['lenderReference']).toEqual(source['lenderReference']);
    expect(response['listingId']).toEqual(source['listingId']);
    expect(response['buyerEmail']).toEqual(source['buyerEmail']);
    expect(response['agentEmail']).toEqual(source['agentEmail']);
  });

  it("entity_schema/dealDb/Offer/response_serializes_enum_fields", () => {
    const source: Record<string, unknown> = {
      financing: Financing.Cash,
      status: OfferStatus.Submitted,
    };
    const response = readAs(OfferResponseDto, source) as Record<string, unknown>;
    expect(response['financing']).toBe(Financing.Cash);
    expect(response['status']).toBe(OfferStatus.Submitted);
  });
});
