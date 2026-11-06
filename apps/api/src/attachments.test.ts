import { test } from 'node:test';
import { strict as assert } from 'node:assert';
import { attachmentHash, identifyAttachment } from './attachments';

test('detects supported signatures and rejects mismatched types', () => {
  const pdf = Buffer.from('%PDF-1.7\n');
  const png = Buffer.from('89504e470d0a1a0a00000000', 'hex');
  assert.equal(identifyAttachment(pdf, 'application/pdf'), 'application/pdf');
  assert.equal(identifyAttachment(png, 'image/png'), 'image/png');
  assert.equal(identifyAttachment(pdf, 'image/png'), null);
  assert.equal(identifyAttachment(Buffer.from('<script>'), 'image/svg+xml'), null);
  assert.equal(identifyAttachment(Buffer.alloc(0), 'audio/mpeg'), null);
  assert.equal(attachmentHash(pdf), attachmentHash(Buffer.from(pdf)));
});
