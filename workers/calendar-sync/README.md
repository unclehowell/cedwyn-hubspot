# HubSpot → Google Calendar sync Worker

A separate, one-way Cloudflare Worker that keeps a private Google Calendar up to date from HubSpot task deadlines and fresh, explicitly dated BucklerFamily.estate roadmap entries.

**HubSpot remains authoritative.** The Worker never creates, edits or closes HubSpot tasks and never sends email. It owns only the Google Calendar events carrying its private extended-property marker.

## Current stage

This is a separate Worker in this repository. It is not yet connected to Google or HubSpot credentials and will remain fail-closed until those are configured.

Do not repurpose the existing `cedwyn-calendar` Worker. That Worker serves the historical estate chronology.

## Data inputs

### HubSpot tasks

The Worker pages through the full open TASK search result, requesting only task ID, subject, status, due timestamp, priority, task type, open state and last-modified timestamp. It does not request or copy task bodies, email text, contacts, attachments or personal correspondence.

A task with no due timestamp is not placed on the calendar. Email-type tasks remain reminders only; they are not proof that an email was drafted or sent.

The Worker uses HubSpot's date-versioned CRM API at `/crm/objects/2026-09/tasks/search`. HubSpot's Service Keys are intended for account-level system-to-system integrations and are the recommended successor to legacy private apps. Create one in Settings → Integrations → Service Keys, scoped to the narrowest available TASK read permission. If the permission picker does not offer task read access, stop and resolve the permission with HubSpot; do not silently broaden it. The Worker performs no HubSpot writes.

### BucklerFamily.estate roadmap

The Worker reads the public Dartboard snapshot at `unclehowell/cedwyn-dartboard/public/data/roadmap.json`. Only entries with an explicit future date, institution and action text are calendarised. The snapshot must have been generated within the previous 36 hours. Older snapshots are reported as stale and are not used to create, update or delete roadmap events.

The snapshot known at implementation time was generated on 9 November 2026 from a 6 November mail manifest. It is stale as of 14 November 2026. No roadmap events will be added until that feed is refreshed; this prevents stale reply expectations becoming live reminders.

Other website pages and arbitrary GitHub issue prose are not scanned for dates. A separate explicit date convention or authoritative feed is required before a source can safely become a calendar entry.

## Event policy

- Runs every 15 minutes after first-run approval. Cloudflare Cron Triggers run in UTC.
- Future HubSpot tasks with the same exact due timestamp are grouped into one event, preserving the original instant and displaying it in `Europe/Amsterdam`.
- Future DEFERRED tasks are included because they have an explicit future schedule. Past-due DEFERRED tasks are excluded from the overdue roll-up.
- Open, past-due NOT_STARTED / IN_PROGRESS / WAITING tasks are summarised in one daily 09:00 Amsterdam triage event, rather than hundreds of backdated appointments. If it is already 09:00 or later, the next morning is used.
- Estate roadmap matters are grouped into all-day events by date.
- Events are private and transparent (they do not block free/busy availability).
- Each event has a deterministic Google event ID and private source marker. Repeated syncs update the same event; they do not create duplicates.
- An event is deleted only when it is one of this Worker's source-marked future reminders that is no longer eligible. Past calendar entries are retained as history. Unrelated user-created events are never touched.
- First owner-approved write is capped at 25 events. Later scheduled syncs can complete the remaining work.

## Cloudflare resources

Cloudflare's account currently has its maximum of 10 D1 databases, so this Worker uses a dedicated EU-jurisdiction **Workers KV** namespace instead of trying to create another D1 database or using a shared database. The KV namespace name is `cedwyn-hubspot-calendar-sync-state`. Its binding is `STATE`. It is separate from existing app namespaces.

KV holds:
- encrypted Google refresh token;
- one-use OAuth state and PKCE verifier (10-minute expiry);
- source-to-event index, content hashes and sync timestamps;
- health/status metadata and a short-lived best-effort sync lock.

The Google refresh token is encrypted with AES-GCM before it is stored in KV. Never put OAuth credentials, Service Keys or encryption keys in Git.

Worker secrets:
- `HUBSPOT_SERVICE_KEY` — read-only HubSpot Service Key;
- `GOOGLE_CLIENT_SECRET` — Google OAuth Web client secret;
- `TOKEN_ENCRYPTION_KEY` — random 32-byte-or-stronger encryption secret;
- `SYNC_ADMIN_PASSWORD` — strong unique password for the private setup endpoints.

Worker variables:
- `GOOGLE_CLIENT_ID` — Google OAuth Web client ID;
- `GOOGLE_REDIRECT_URI` — exact callback URL `https://<worker-host>/oauth/google/callback`;
- `SYNC_ADMIN_USER` — HTTP Basic username (defaults to `calendar-admin`);
- `HUBSPOT_PORTAL_ID` — portal ID (defaults to `149419802`);
- optional `HUBSPOT_TASKS_SEARCH_URL` — endpoint override for account-specific API availability;
- `STATE` — Workers KV binding.

Enable Google Calendar API in Google Cloud. Create a Web application OAuth client and register the exact callback URL. The only Calendar scope requested is `https://www.googleapis.com/auth/calendar.events.owned`, which is limited to calendars the account owns. It does not ask to read other calendars or calendar settings.

## One-time activation sequence

1. Deploy the Worker to its own `workers.dev` hostname. No custom domain, route, DNS or existing Worker is changed.
2. Set the four secrets and the Google OAuth / portal variables above in Cloudflare.
3. Open `/admin/google/start` in a browser, authenticate using the private admin credentials, then complete Google's consent screen once. The callback stores the refresh token encrypted.
4. Configure the HubSpot Service Key and confirm `/health` reports both sources connected.
5. POST `/admin/sync?mode=dry-run` with HTTP Basic authentication. Review counts, source freshness and sample events. No Google writes occur during dry run.
6. Only after the dry-run result is acceptable, POST `/admin/sync?mode=apply`. This is the explicit first-write approval and is capped at 25 calendar events.
7. The `*/15 * * * *` Cron Trigger then runs automatically. Later runs reconcile changed / completed tasks, update existing events and add new ones.

The Worker stays fail-closed if the first sync has not been approved. Merely adding credentials will not create calendar events.

## Operations

- `GET /health`: connection state, source freshness, last run and error summary. No tokens or task bodies are returned.
- `GET /admin/google/start`: admin-authenticated Google OAuth start.
- `GET /oauth/google/callback`: Google OAuth callback protected by state and PKCE.
- `POST /admin/sync?mode=dry-run`: read sources and report a proposed sync without Google writes.
- `POST /admin/sync?mode=apply`: first owner-approved write (25-event cap).
- `POST /admin/sync?mode=continue`: authenticated continuation after first approval.
- Cron: automatic reconciliation every 15 minutes after approval.

## Tests

Run domain tests from the repository root:

```sh
node --test workers/calendar-sync/tests/*.test.mjs
```

Integration tests against Google and HubSpot should use mocks or test credentials in a non-production account. Never use a live send or HubSpot write to test this Worker; its only external write capability is Google Calendar event management.
