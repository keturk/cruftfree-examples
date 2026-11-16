import { validate } from 'class-validator';
import { instanceToPlain, plainToInstance } from 'class-transformer';
import { ListingFacts } from '../src/dto/listing-facts.struct';
import { ListingStatus } from '../src/enums/listing-status.enum';

describe('ListingFacts Struct', () => {
  function buildValidPayload(): Record<string, unknown> {
    return {
      title: 'hello',
      status: ListingStatus.Draft,
      price: '49.95',
      agentName: 'hello',
      agentEmail: 'hello@world.com',
    };
  }

  it("struct/ListingFacts/create_instance", () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(ListingFacts, payload);
    expect(instance).toBeDefined();
    expect(instance.title).toBeDefined();
    expect(instance.status).toBeDefined();
    expect(instance.price).toBeDefined();
    expect(instance.agentName).toBeDefined();
    expect(instance.agentEmail).toBeDefined();
  });

  it("struct/ListingFacts/passes_validation", async () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(ListingFacts, payload);
    const errors = await validate(instance);
    expect(errors.length).toBe(0);
  });

  it("struct/ListingFacts/title/required", async () => {
    const payload = buildValidPayload();
    delete payload.title;
    const instance = plainToInstance(ListingFacts, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/ListingFacts/status/required", async () => {
    const payload = buildValidPayload();
    delete payload.status;
    const instance = plainToInstance(ListingFacts, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/ListingFacts/price/required", async () => {
    const payload = buildValidPayload();
    delete payload.price;
    const instance = plainToInstance(ListingFacts, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/ListingFacts/agentName/required", async () => {
    const payload = buildValidPayload();
    delete payload.agentName;
    const instance = plainToInstance(ListingFacts, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/ListingFacts/agentEmail/required", async () => {
    const payload = buildValidPayload();
    delete payload.agentEmail;
    const instance = plainToInstance(ListingFacts, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/ListingFacts/serialization_round_trip", () => {
    const instance = plainToInstance(ListingFacts, buildValidPayload());
    const restored = plainToInstance(ListingFacts, instanceToPlain(instance));
    expect(restored).toEqual(instance);
  });
});
