import { createHash } from 'node:crypto';

export const MAX_ATTACHMENT_BYTES = 20 * 1024 * 1024;

export function identifyAttachment(bytes: Buffer, declared: string): string | null {
  const starts = (hex: string) => bytes.subarray(0, hex.length / 2).equals(Buffer.from(hex, 'hex'));
  const ascii = (offset: number, length: number) => bytes.subarray(offset, offset + length).toString('ascii');
  if (declared === 'application/pdf' && ascii(0, 5) === '%PDF-') return declared;
  if (declared === 'image/jpeg' && starts('ffd8ff')) return declared;
  if (declared === 'image/png' && starts('89504e470d0a1a0a')) return declared;
  if (declared === 'image/gif' && ['GIF87a', 'GIF89a'].includes(ascii(0, 6))) return declared;
  if (declared === 'image/webp' && ascii(0, 4) === 'RIFF' && ascii(8, 4) === 'WEBP') return declared;
  if (declared === 'audio/wav' && ascii(0, 4) === 'RIFF' && ascii(8, 4) === 'WAVE') return declared;
  if (declared === 'audio/mpeg' && (ascii(0, 3) === 'ID3' || (bytes.length >= 2 && bytes[0] === 0xff && (bytes[1] & 0xe0) === 0xe0))) return declared;
  if ((declared === 'audio/ogg' || declared === 'video/ogg') && ascii(0, 4) === 'OggS') return declared;
  if ((declared === 'audio/webm' || declared === 'video/webm') && starts('1a45dfa3')) return declared;
  if ((declared === 'audio/mp4' || declared === 'video/mp4') && ascii(4, 4) === 'ftyp') return declared;
  return null;
}

export function attachmentHash(bytes: Buffer): string {
  return createHash('sha256').update(bytes).digest('hex');
}
