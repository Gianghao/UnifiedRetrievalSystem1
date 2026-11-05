import { test } from 'node:test';
import { strict as assert } from 'node:assert';
import { codeHash, normalizePhone, safeEqual, newCode, newToken, hashToken } from './core';

test('normalizes only valid international numbers', () => {
  assert.equal(normalizePhone('+1 202 555 0123'), '+12025550123');
  assert.throws(() => normalizePhone('123'));
});
test('verification codes bind phone and purpose', () => {
  const hash = codeHash('+12025550123', 'signin', '123456', 'secret');
  assert.ok(safeEqual(hash, codeHash('+12025550123', 'signin', '123456', 'secret')));
  assert.ok(!safeEqual(hash, codeHash('+12025550123', 'register', '123456', 'secret')));
  assert.match(newCode(), /^\d{6}$/);
  assert.notEqual(hashToken(newToken()), hashToken(newToken()));
});
