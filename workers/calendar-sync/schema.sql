-- Dedicated D1 schema for the HubSpot → Google Calendar sync Worker.
-- Do not put this in the shared cedwyn-apps database.

CREATE TABLE IF NOT EXISTS cal_sync_meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cal_sync_tokens (
  id TEXT PRIMARY KEY,
  refresh_ciphertext TEXT NOT NULL,
  refresh_iv TEXT NOT NULL,
  calendar_id TEXT NOT NULL DEFAULT 'primary',
  connected_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cal_oauth_states (
  state_hash TEXT PRIMARY KEY,
  code_verifier TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  expires_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS cal_oauth_states_expiry_idx
  ON cal_oauth_states(expires_at);

CREATE TABLE IF NOT EXISTS cal_sync_events (
  source_type TEXT NOT NULL,
  source_key TEXT NOT NULL,
  event_id TEXT NOT NULL UNIQUE,
  content_hash TEXT NOT NULL,
  source_members_json TEXT NOT NULL DEFAULT '[]',
  synced_at TEXT NOT NULL,
  PRIMARY KEY(source_type, source_key)
);

CREATE INDEX IF NOT EXISTS cal_sync_events_source_idx
  ON cal_sync_events(source_type);

CREATE TABLE IF NOT EXISTS cal_sync_lock (
  id TEXT PRIMARY KEY,
  owner TEXT,
  lease_until INTEGER NOT NULL DEFAULT 0
);

INSERT OR IGNORE INTO cal_sync_lock (id, owner, lease_until)
VALUES ('sync', NULL, 0);
