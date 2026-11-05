import { createHash, createHmac, randomBytes, randomInt, timingSafeEqual } from 'node:crypto';
import { parsePhoneNumberFromString } from 'libphonenumber-js';

export function normalizePhone(value: string): string {
  const parsed = parsePhoneNumberFromString(value);
  if (!value.startsWith('+') || !parsed?.isValid()) throw new Error('Enter a valid international phone number beginning with +.');
  return parsed.number;
}
export const hashToken = (value: string) => createHash('sha256').update(value).digest('hex');
export const newToken = () => randomBytes(32).toString('base64url');
export const newCode = () => randomInt(0, 1_000_000).toString().padStart(6, '0');
export const codeHash = (phone: string, purpose: string, code: string, secret: string) => createHmac('sha256', secret).update(`${phone}:${purpose}:${code}`).digest('hex');
export function safeEqual(a: string, b: string) {
  const x = Buffer.from(a, 'hex'); const y = Buffer.from(b, 'hex');
  return x.length === y.length && timingSafeEqual(x, y);
}
