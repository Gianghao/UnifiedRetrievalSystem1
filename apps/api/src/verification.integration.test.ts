import { test } from 'node:test';
import { strict as assert } from 'node:assert';
import { randomBytes } from 'node:crypto';
import { Pool } from 'pg';
import { issueVerification, lockVerification } from './verification';

const connectionString = process.env.TEST_DATABASE_URL;
test('concurrent OTP requests leave one active code and serialize with verification', { skip: !connectionString }, async () => {
  const schema = `otp_test_${randomBytes(8).toString('hex')}`;
  const admin = new Pool({ connectionString });
  await admin.query(`CREATE SCHEMA "${schema}"`);
  const pool = new Pool({ connectionString, options: `-c search_path=${schema}` });
  try {
    await pool.query('CREATE TABLE phone_verifications (phone text, purpose text, code_hash text, expires_at timestamptz, consumed_at timestamptz)');
    const number = '+12025550123';
    await Promise.all(Array.from({length: 20}, (_, i) => issueVerification(pool, number, 'signin', String(i))));
    const result = await pool.query('SELECT code_hash FROM phone_verifications WHERE consumed_at IS NULL');
    assert.equal(result.rowCount, 1);
    const verifier = await pool.connect();
    try {
      await verifier.query('BEGIN');
      await lockVerification(verifier, number, 'signin');
      const pending = issueVerification(pool, number, 'signin', 'new');
      const lockState = await pool.query("SELECT count(*)::int AS count FROM pg_locks WHERE locktype='advisory' AND granted=false");
      // Ensure the issuing transaction reaches the lock before releasing verification.
      let waiting = lockState.rows[0].count > 0;
      for (let i = 0; !waiting && i < 100; i++) {
        await new Promise(resolve => setTimeout(resolve, 10));
        waiting = (await pool.query("SELECT count(*)::int AS count FROM pg_locks WHERE locktype='advisory' AND granted=false")).rows[0].count > 0;
      }
      assert.ok(waiting, 'issuer should wait for the verification lock');
      await verifier.query('COMMIT');
      await pending;
    } finally { await verifier.query('ROLLBACK'); verifier.release(); }
    assert.deepEqual((await pool.query('SELECT code_hash FROM phone_verifications WHERE consumed_at IS NULL')).rows, [{code_hash:'new'}]);
  } finally {
    await pool.end();
    await admin.query(`DROP SCHEMA "${schema}" CASCADE`);
    await admin.end();
  }
});
