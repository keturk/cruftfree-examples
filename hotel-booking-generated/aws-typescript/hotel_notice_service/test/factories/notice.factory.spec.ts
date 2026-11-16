import { buildNotice } from './notice.factory';

describe('buildNotice', () => {
  it("entity_factory/noticeDb/Notice/valid_instance", () => {
    const result = buildNotice();
    expect(result).toBeDefined();
    expect(result.recipient).toBeDefined();
    expect(result.subject).toBeDefined();
    expect(result.body).toBeDefined();
    expect(result.noticeKey).toBeDefined();
  });

  it("entity_factory/noticeDb/Notice/applies_overrides", () => {
    const overrides = {
      recipient: 'test',
    };
    const result = buildNotice(overrides);
    expect(result.recipient).toBe(overrides.recipient);
  });

  it("entity_factory/noticeDb/Notice/distinct_instances", () => {
    const a = buildNotice();
    const b = buildNotice();
    expect(a).not.toBe(b);
  });
});
