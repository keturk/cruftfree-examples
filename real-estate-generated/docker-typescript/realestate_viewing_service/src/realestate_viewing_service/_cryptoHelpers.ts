/**
 * Crypto helper functions for generated TypeScript code.
 *
 * The signing key is the secret the declared key handle names, resolved through the secrets
 * service on every call so a rotated key is used by the next signature. No environment variable
 * is read.
 */
import { createCipheriv, createDecipheriv, createHmac, createSign, randomBytes } from 'crypto';
import { SecretsService } from "./secrets/secrets.service";

const secrets = new SecretsService();

export async function _cryptoSign(
  keyId: string,
  message: string,
  signingAlgorithm: string,
): Promise<string> {
  const key = await secrets.getSecret(keyId);
  if (!key) {
    throw new Error(
      `Signing key '${keyId}' resolved to an empty value from the secrets service. Ensure the ` +
        'handle is declared in the service secrets table and provisioned with a non-empty value.',
    );
  }
  const normalized = signingAlgorithm.toLowerCase();
  if (normalized.includes('hmac') || normalized.includes('sha256')) {
    return createHmac('sha256', key).update(message).digest('base64url');
  }
  const signer = createSign(signingAlgorithm);
  signer.update(message);
  signer.end();
  return signer.sign(key, 'base64url');
}

const HASH_ALGORITHMS: Readonly<Record<string, string>> = {
  SHA256: 'sha256',
  SHA1: 'sha1',
  MD5: 'md5',
  SHA512: 'sha512',
};

/*
 * `Crypto.encrypt` / `Crypto.decrypt`, the same scheme on every target: AES-256-GCM with no
 * associated data. The key is 32 bytes in base64url (43 characters, optionally one trailing
 * '='); the ciphertext is unpadded base64url of nonce, ciphertext, tag.
 */
const CIPHER_KEY_BYTES = 32;
const CIPHER_NONCE_BYTES = 12;
const CIPHER_TAG_BYTES = 16;
const CIPHER_KEY_TEXT = /^[A-Za-z0-9_-]{43}=?$/;
const CIPHERTEXT_TEXT = /^[A-Za-z0-9_-]+$/;
const CIPHER_KEY_ERROR =
  "Crypto key must be 32 bytes written in base64url: 43 characters of A-Z a-z 0-9 - _, " +
  "optionally followed by one '='. Generate it from 32 random bytes and keep it in a secret.";
const CIPHERTEXT_ERROR =
  'Crypto.decrypt: the value is not a ciphertext this key produced; it is malformed, ' +
  'was altered, or was encrypted under another key.';

/** The bytes `text` encodes in canonical base64url; throws `error` for anything else. */
function decodeBase64Url(text: string, pattern: RegExp, error: string): Buffer {
  if (!pattern.test(text)) {
    throw new Error(error);
  }
  const unpadded = text.replace(/=+$/, '');
  const raw = Buffer.from(unpadded, 'base64url');
  if (raw.toString('base64url') !== unpadded) {
    throw new Error(error);
  }
  return raw;
}

/** The AES-256 key `key` writes in base64url; throws for any other text. */
function cipherKey(key: string): Buffer {
  const secret = decodeBase64Url(key, CIPHER_KEY_TEXT, CIPHER_KEY_ERROR);
  if (secret.length !== CIPHER_KEY_BYTES) {
    throw new Error(CIPHER_KEY_ERROR);
  }
  return secret;
}

/** Throws unless `key` is an AES-256 key written in base64url (an encrypted column's boot check). */
export function _cryptoCheckCipherKey(key: string): void {
  cipherKey(key);
}

/** `Crypto.encrypt`: AES-256-GCM under a fresh random nonce. */
export function _cryptoEncrypt(plaintext: string, key: string): string {
  const nonce = randomBytes(CIPHER_NONCE_BYTES);
  const cipher = createCipheriv('aes-256-gcm', cipherKey(key), nonce, { authTagLength: CIPHER_TAG_BYTES });
  const body = Buffer.concat([cipher.update(plaintext, 'utf8'), cipher.final()]);
  return Buffer.concat([nonce, body, cipher.getAuthTag()]).toString('base64url');
}

/** `Crypto.decrypt`: authenticate and decrypt a `Crypto.encrypt` value; throws when it is not authentic. */
export function _cryptoDecrypt(ciphertext: string, key: string): string {
  const secret = cipherKey(key);
  const sealed = decodeBase64Url(ciphertext, CIPHERTEXT_TEXT, CIPHERTEXT_ERROR);
  if (sealed.length < CIPHER_NONCE_BYTES + CIPHER_TAG_BYTES) {
    throw new Error(CIPHERTEXT_ERROR);
  }
  const nonce = sealed.subarray(0, CIPHER_NONCE_BYTES);
  const body = sealed.subarray(CIPHER_NONCE_BYTES, sealed.length - CIPHER_TAG_BYTES);
  const decipher = createDecipheriv('aes-256-gcm', secret, nonce, { authTagLength: CIPHER_TAG_BYTES });
  decipher.setAuthTag(sealed.subarray(sealed.length - CIPHER_TAG_BYTES));
  try {
    return Buffer.concat([decipher.update(body), decipher.final()]).toString('utf8');
  } catch {
    throw new Error(CIPHERTEXT_ERROR);
  }
}

/** The Node hash name of the CruftFree hash algorithm `name` (any letter case). */
export function _cryptoHashAlgorithm(name: string): string {
  const algorithm = HASH_ALGORITHMS[name.toUpperCase()];
  if (algorithm === undefined) {
    throw new Error(
      `Unsupported hash algorithm '${name}'; valid algorithms: ${Object.keys(HASH_ALGORITHMS).sort().join(', ')}`,
    );
  }
  return algorithm;
}
