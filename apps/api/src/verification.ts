import type { Pool, PoolClient } from 'pg';

export async function lockVerification(client: PoolClient, phone: string, purpose: string) {
  await client.query('SELECT pg_advisory_xact_lock(hashtextextended($1, 0))', [`${phone}:${purpose}`]);
}

export async function issueVerification(pool: Pool, phone: string, purpose: string, codeHash: string) {
  const client = await pool.connect();
  try {
    await client.query('BEGIN');
    await lockVerification(client, phone, purpose);
    await client.query('UPDATE phone_verifications SET consumed_at=now() WHERE phone=$1 AND purpose=$2 AND consumed_at IS NULL', [phone, purpose]);
    await client.query("INSERT INTO phone_verifications(phone,purpose,code_hash,expires_at) VALUES($1,$2,$3,now()+interval '10 minutes')", [phone, purpose, codeHash]);
    await client.query('COMMIT');
  } catch (err) {
    await client.query('ROLLBACK');
    throw err;
  } finally {
    client.release();
  }
}
