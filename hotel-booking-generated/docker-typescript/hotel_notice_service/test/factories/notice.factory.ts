import { Notice } from '../../src/hotel_notice_service/entities/notice_db/notice.entity';

/**
 * Build a partial Notice with sensible defaults for testing.
 * Override any field via the `overrides` parameter.
 */
export function buildNotice(
  overrides?: Partial<Notice>,
): Partial<Notice> {
  return {
    recipient: 'test',
    subject: 'test',
    body: 'test',
    noticeKey: `test_${crypto.randomUUID().replace(/-/g, '').slice(0, 8)}`,
    ...overrides,
  };
}
