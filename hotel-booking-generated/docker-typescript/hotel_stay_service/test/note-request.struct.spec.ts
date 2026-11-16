import { validate } from 'class-validator';
import { instanceToPlain, plainToInstance } from 'class-transformer';
import { NoteRequest } from '../src/dto/note-request.struct';

describe('NoteRequest Struct', () => {
  function buildValidPayload(): Record<string, unknown> {
    return {
      stayId: '7c9e6679-7425-40de-944b-e07fc1f90ae7',
      note: 'world',
    };
  }

  it("struct/NoteRequest/create_instance", () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(NoteRequest, payload);
    expect(instance).toBeDefined();
    expect(instance.stayId).toBeDefined();
    expect(instance.note).toBeDefined();
  });

  it("struct/NoteRequest/passes_validation", async () => {
    const payload = buildValidPayload();
    const instance = plainToInstance(NoteRequest, payload);
    const errors = await validate(instance);
    expect(errors.length).toBe(0);
  });

  it("struct/NoteRequest/stayId/required", async () => {
    const payload = buildValidPayload();
    delete payload.stayId;
    const instance = plainToInstance(NoteRequest, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/NoteRequest/note/required", async () => {
    const payload = buildValidPayload();
    delete payload.note;
    const instance = plainToInstance(NoteRequest, payload);
    const errors = await validate(instance);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("struct/NoteRequest/serialization_round_trip", () => {
    const instance = plainToInstance(NoteRequest, buildValidPayload());
    const restored = plainToInstance(NoteRequest, instanceToPlain(instance));
    expect(restored).toEqual(instance);
  });
});
