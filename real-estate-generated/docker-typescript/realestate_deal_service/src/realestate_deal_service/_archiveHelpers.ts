/**
 * Archive helpers for the CruftFree ``Archive.entries`` / ``Archive.zip`` builtins.
 * Reads a ZIP archive's regular members under required entry-count and byte
 * limits enforced while reading, and bundles in-memory maps into ZIP bytes.
 */

import AdmZip from 'adm-zip';
import { inflateRawSync } from 'node:zlib';

/** An archive read or write failed: corrupt data, a limit exceeded, or an escaping member path. */
export class ArchiveError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ArchiveError';
  }
}

/** One regular archive member, as the generated `ArchiveEntry` interface holds it. */
export interface ArchiveEntryRecord {
  path: string;
  content: Buffer;
}

const ZIP_METHOD_STORE = 0;
const ZIP_METHOD_DEFLATE = 8;
const ZIP_FLAG_ENCRYPTED = 0x1;

const CRC32_TABLE: Uint32Array = (() => {
  const table = new Uint32Array(256);
  for (let n = 0; n < 256; n += 1) {
    let c = n;
    for (let k = 0; k < 8; k += 1) {
      c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    }
    table[n] = c >>> 0;
  }
  return table;
})();

function _archiveCrc32(data: Buffer): number {
  let crc = 0xffffffff;
  for (const byte of data) {
    crc = CRC32_TABLE[(crc ^ byte) & 0xff] ^ (crc >>> 8);
  }
  return (crc ^ 0xffffffff) >>> 0;
}

function _archiveLimit(label: string, value: number): number {
  if (typeof value !== 'number' || !Number.isInteger(value) || value < 1) {
    throw new ArchiveError(`Archive.entries ${label} must be a positive integer; got ${String(value)}.`);
  }
  return value;
}

function _archiveCause(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

/**
 * Decompress one member, stopping as soon as it exceeds the remaining byte
 * `budget`: the inflater is given a ceiling, so an expanding member is never
 * inflated whole.
 */
function _archiveReadMember(entry: AdmZip.IZipEntry, budget: number): Buffer {
  const name = JSON.stringify(entry.entryName);
  const overLimit = new ArchiveError(
    `Archive.entries: member ${name} expands past the maxBytes limit; the archive was not read further.`,
  );
  if ((entry.header.flags & ZIP_FLAG_ENCRYPTED) !== 0) {
    throw new ArchiveError(`Archive.entries: member ${name} is encrypted, which is not supported.`);
  }
  let content: Buffer;
  try {
    const compressed = entry.getCompressedData();
    if (entry.header.method === ZIP_METHOD_STORE) {
      content = compressed;
    } else if (entry.header.method === ZIP_METHOD_DEFLATE) {
      content = inflateRawSync(compressed, { maxOutputLength: budget + 1 });
    } else {
      throw new ArchiveError(
        `Archive.entries: member ${name} uses compression method ${entry.header.method}, which is not supported.`,
      );
    }
  } catch (error) {
    if (error instanceof ArchiveError) {
      throw error;
    }
    if ((error as NodeJS.ErrnoException).code === 'ERR_BUFFER_TOO_LARGE') {
      throw overLimit;
    }
    throw new ArchiveError(`Archive.entries: member ${name} cannot be read (${_archiveCause(error)}); the archive is corrupt.`);
  }
  if (content.length > budget) {
    throw overLimit;
  }
  if (content.length !== entry.header.size || _archiveCrc32(content) !== entry.header.crc) {
    throw new ArchiveError(`Archive.entries: member ${name} fails its size or checksum; the archive is corrupt.`);
  }
  return content;
}

/**
 * Read every regular member of a ZIP archive as `{path, content}`, in archive
 * order. Both limits are required: the entry count is checked before any member
 * is read, the byte total as each member is decompressed.
 */
export function _archiveEntries(rawData: Buffer, maxEntries: number, maxBytes: number): ArchiveEntryRecord[] {
  const entryLimit = _archiveLimit('maxEntries', maxEntries);
  const byteLimit = _archiveLimit('maxBytes', maxBytes);
  if (!Buffer.isBuffer(rawData)) {
    throw new ArchiveError(`Archive.entries expects the archive as Bytes; got ${typeof rawData}.`);
  }
  let zip: AdmZip;
  try {
    zip = new AdmZip(rawData);
  } catch (error) {
    throw new ArchiveError(`Archive.entries: the data is not a valid ZIP archive (${_archiveCause(error)}).`);
  }
  const infos = zip.getEntries();
  if (infos.length > entryLimit) {
    throw new ArchiveError(
      `Archive.entries: the archive holds ${infos.length} entries, over the maxEntries limit of ${entryLimit}.`,
    );
  }
  const entries: ArchiveEntryRecord[] = [];
  let budget = byteLimit;
  for (const info of infos) {
    const path = _archiveMemberName(info.entryName, 'Archive.entries', ArchiveError);
    if (info.isDirectory) {
      continue;
    }
    const content = _archiveReadMember(info, budget);
    budget -= content.length;
    entries.push({ path, content });
  }
  return entries;
}

export interface ArchiveZipOptions {
  /** DEFLATE members (default) or STORE them for already-compressed content. */
  compress?: boolean;
}

const ARCHIVE_ZIP_OPTION_KEYS: ReadonlySet<string> = new Set(['compress']);
/** Fixed member timestamp (the ZIP epoch) so identical inputs give identical bytes. */
const ARCHIVE_FIXED_MEMBER_TIME = new Date(1980, 0, 1, 0, 0, 0);

/**
 * Validate one member name: a relative POSIX path inside the archive. An
 * absolute path, a drive letter, a `.`/`..` segment, a backslash or a NUL would
 * let the archive escape its extraction directory, so they are rejected here
 * rather than shipped to whoever unpacks it.
 */
function _archiveMemberName(
  name: string,
  operation: string = 'Archive.zip',
  ErrorType: new (message: string) => Error = Error,
): string {
  if (name === '' || name === '/') {
    throw new ErrorType(
      `${operation} member name must not be empty. Use a relative path such as 'report.html' or 'reports/2024/' for an empty directory.`,
    );
  }
  if (name.includes('\0') || name.includes('\\')) {
    throw new ErrorType(
      `${operation} member name ${JSON.stringify(name)} contains a NUL or backslash; use '/' as the separator and printable characters only.`,
    );
  }
  if (name.startsWith('/') || (name.length > 1 && name[1] === ':')) {
    throw new ErrorType(
      `${operation} member name ${JSON.stringify(name)} is absolute; member names must be relative to the archive root (for example 'reports/report-1.html').`,
    );
  }
  if (name.split('/').some((segment) => segment === '.' || segment === '..')) {
    throw new ErrorType(
      `${operation} member name ${JSON.stringify(name)} contains a '.' or '..' segment; an archive member must not be able to escape the directory it is unpacked into.`,
    );
  }
  return name;
}

function _archiveZipCompress(options: ArchiveZipOptions | undefined): boolean {
  if (options === undefined || options === null) {
    return true;
  }
  if (typeof options !== 'object' || Array.isArray(options)) {
    throw new Error(`Archive.zip options must be an object such as {compress: false}; got ${typeof options}.`);
  }
  const unknown = Object.keys(options).filter((key) => !ARCHIVE_ZIP_OPTION_KEYS.has(key)).sort();
  if (unknown.length > 0) {
    throw new Error(
      `Archive.zip received unknown option(s) ${JSON.stringify(unknown)}; valid options: ${JSON.stringify([...ARCHIVE_ZIP_OPTION_KEYS])}.`,
    );
  }
  const compress = options.compress ?? true;
  if (typeof compress !== 'boolean') {
    throw new Error(
      `Archive.zip option 'compress' must be a Boolean (true = DEFLATE, false = STORE for already-compressed members); got ${typeof compress}.`,
    );
  }
  return compress;
}

/**
 * Bundle `{memberName: bytes}` into a ZIP archive that `_archiveEntries` reads
 * back with the same names and bytes. A key ending in `/` creates an empty directory entry (it
 * must map to an empty Buffer). Members are written in key order with a fixed
 * timestamp, so the same input always yields the same bytes.
 */
export function _archiveZip(files: Record<string, Buffer>, options?: ArchiveZipOptions): Buffer {
  if (files === null || typeof files !== 'object' || Array.isArray(files)) {
    throw new Error(`Archive.zip expects a Map<String, Bytes> of member name to content; got ${typeof files}.`);
  }
  const compress = _archiveZipCompress(options);
  const zip = new AdmZip();
  for (const [rawName, content] of Object.entries(files)) {
    const name = _archiveMemberName(rawName);
    if (!Buffer.isBuffer(content)) {
      throw new Error(
        `Archive.zip member ${JSON.stringify(name)} must map to Bytes; got ${typeof content}. Encode text with String.toBytes first.`,
      );
    }
    const isDirectory = name.endsWith('/');
    if (isDirectory && content.length > 0) {
      throw new Error(
        `Archive.zip member ${JSON.stringify(name)} names a directory (trailing '/') but carries content; directory entries must map to empty Bytes.`,
      );
    }
    const entry = zip.addFile(name, isDirectory ? Buffer.alloc(0) : content);
    entry.header.time = ARCHIVE_FIXED_MEMBER_TIME;
    // ZIP method 8 is DEFLATE, 0 is STORE; a directory entry has no data to compress.
    entry.header.method = compress && !isDirectory ? 8 : 0;
  }
  return zip.toBuffer();
}
