CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE TABLE users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(), phone text NOT NULL UNIQUE,
  display_name text NOT NULL CHECK (length(display_name) BETWEEN 1 AND 80), created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE phone_verifications (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(), phone text NOT NULL, purpose text NOT NULL CHECK (purpose IN ('register','signin')),
  code_hash text NOT NULL, expires_at timestamptz NOT NULL, attempts integer NOT NULL DEFAULT 0, consumed_at timestamptz, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX phone_verification_lookup ON phone_verifications(phone, purpose, created_at DESC);
CREATE TABLE auth_sessions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(), user_id uuid NOT NULL REFERENCES users ON DELETE CASCADE,
  token_hash text NOT NULL UNIQUE, expires_at timestamptz NOT NULL, revoked_at timestamptz, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE contacts (
  owner_id uuid NOT NULL REFERENCES users ON DELETE CASCADE, phone text NOT NULL, created_at timestamptz NOT NULL DEFAULT now(), PRIMARY KEY(owner_id,phone)
);
CREATE TABLE conversations (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), pair_key text NOT NULL UNIQUE, created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE conversation_members (conversation_id uuid NOT NULL REFERENCES conversations ON DELETE CASCADE, user_id uuid NOT NULL REFERENCES users ON DELETE CASCADE, PRIMARY KEY(conversation_id,user_id));
CREATE INDEX membership_user ON conversation_members(user_id,conversation_id);
CREATE TABLE messages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(), conversation_id uuid NOT NULL REFERENCES conversations ON DELETE CASCADE,
  sender_id uuid NOT NULL REFERENCES users ON DELETE CASCADE, client_id uuid NOT NULL, body text NOT NULL CHECK (length(body) BETWEEN 1 AND 5000),
  sent_at timestamptz NOT NULL DEFAULT clock_timestamp(), edited_at timestamptz, deleted_at timestamptz,
  UNIQUE(sender_id,client_id)
);
CREATE INDEX messages_page ON messages(conversation_id,sent_at DESC,id DESC);
CREATE TABLE message_receipts (message_id uuid NOT NULL REFERENCES messages ON DELETE CASCADE, user_id uuid NOT NULL REFERENCES users ON DELETE CASCADE, delivered_at timestamptz, read_at timestamptz, PRIMARY KEY(message_id,user_id));
