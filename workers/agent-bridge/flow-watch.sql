-- Cedwyn flow-watch ledger; namespaced tables in existing cedwyn-apps D1.
CREATE TABLE IF NOT EXISTS cw_flow_watch_state (
  id TEXT PRIMARY KEY,
  checked_at TEXT,
  trigger_type TEXT,
  overall_status TEXT,
  main_sha TEXT,
  live_sha TEXT,
  snapshot_json TEXT,
  lease_until TEXT
);
CREATE TABLE IF NOT EXISTS cw_flow_watch_issues (
  event_key TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  severity TEXT NOT NULL,
  status TEXT NOT NULL,
  first_seen TEXT NOT NULL,
  last_seen TEXT NOT NULL,
  resolved_at TEXT,
  detail_json TEXT
);
CREATE INDEX IF NOT EXISTS cw_flow_watch_issues_status_idx
  ON cw_flow_watch_issues(status, last_seen);
CREATE TABLE IF NOT EXISTS cw_flow_watch_activity (
  event_id TEXT PRIMARY KEY,
  received_at TEXT NOT NULL,
  source TEXT NOT NULL,
  event_type TEXT NOT NULL,
  action TEXT,
  workflow_name TEXT,
  job_name TEXT,
  run_id TEXT,
  head_sha TEXT,
  branch TEXT,
  status TEXT,
  conclusion TEXT,
  detail_json TEXT
);
