CREATE TABLE IF NOT EXISTS attachments (
  message_id uuid PRIMARY KEY REFERENCES messages(id) ON DELETE CASCADE,
  filename text NOT NULL,
  mime_type text NOT NULL,
  size_bytes integer NOT NULL,
  sha256 text NOT NULL,
  content bytea,
  expires_at timestamptz NOT NULL
);
CREATE INDEX IF NOT EXISTS attachments_expiry ON attachments(expires_at) WHERE content IS NOT NULL;
