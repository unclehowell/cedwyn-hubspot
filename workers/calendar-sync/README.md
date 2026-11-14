# HubSpot → Google Calendar sync Worker

A separate, one-way Cloudflare Worker that keeps a private Google Calendar up to date from HubSpot task deadlines and fresh, explicitly dated BucklerFamily.estate roadmap entries.

**HubSpot remains authoritative.** The Worker never creates, edits or closes HubSpot tasks and never sends email. It owns only the Google Calendar events carrying its private extended-property marker.

## Current stage

This folder is a proposed Worker implementation. It is not deployed or connected to credentials. It must remain disabled until the owner completes the one-time Google OAuth connection and supplies a read-only HubSpot Service Key through Cloudflare's secret manager.

Do not repurpose the existing `cedwyn-calendar` Worker. That Worker serves the historical estate chronology.

## Data inputs

### HubSpot tasks

The Worker pages through the full open TASK search result, requesting only:

- task ID and subject;
- status, due timestamp, priority and task type;
- open state and last-modified timestamp.

It does not request or copy task bodies, email text, contacts, attachments or personal correspondence. A task with no due timestamp is not placed on the calendar. Email-type tasks remain reminders only; they are not proof that an email was drafted or sent.

HubSpot's date-versioned CRM API is used by default at `/crm/objects/2026-09/tasks/search`. Set `HUBSPOT_TASKS_SEARCH_URL` only if HubSpot's account-specific API availability requires a supported alternative. No legacy private app is required; use a HubSpot Service Key for this account-level integration.

Create the Service Key in HubSpot Settings → Integrations → Service Keys. Select the narrowest available read permission for TASK records. If the task-read scope is not offered by the account's scope selector, stop and resolve the permission with HubSpot; do not silently broaden access. The Worker performs no HubSpot writes.

### BucklerFamily.estate roadmap

The Worker reads the public Dartboard snapshot at:

`unclehowell/cedwyn-dartboard/public/data/roadmap.json`

Only entries with an explicit future date, institution and action text are calendarised. The snapshot must have been generated within the previous 36 hours. Older snapshots are reported as stale and are not used to create, update or delete roadmap events.

The snapshot currently known at implementation time was generated on 9 November 2026 from a 6 November mail manifest. It is stale as of 14 November 2026. No dated roadmap events will be added until that source is refreshed. This is intentional: the Worker must not turn stale reply expectations into current deadlines.

Other website pages and arbitrary GitHub issue prose are not scanned for dates. A separate explicit date convention or an authoritative feed is required before a source can safely become a calendar entry.

## Event policy

- Runs every 15 minutes after first-run approval.
- Future HubSpot tasks with the same exact due timestamp are grouped into one event, preserving the original instant and displaying it in `Europe/Amsterdam`.
- Future DEFERRED tasks are included because they have an explicit future schedule. Past-due DEFERRED tasks are excluded from the overdue roll-up.
- Open, past-due NOT_STARTED / IN_PROGRESS / WAITING tasks are summarised in one daily 09:00 Amsterdam triage event, rather than hundreds of backdated appointments.
- Estate roadmap matters are grouped into all-day events by date.
- Events are private and transparent (they do not block free/busy availability).
- Each event has a deterministic Google event ID and private source marker. Repeated syncs update the same event; they do not create duplicates.
- An event is deleted only when it is one of this Worker's source-marked future reminders that is no longer eligible. Past calendar entries are retained as history. Unrelated user-created events are never touched.
- First owner-approved write is capped at 25 events. Later scheduled syncs can complete the remaining work.

## Cloudflare resources

Create a **new dedicated D1 database** for this Worker. Do not reuse the shared `cedwyn-apps` D1 database.

Run `schema.sql` against that database and bind it to the Worker as `DB`.

Worker secrets (never store in Git):

| Secret / binding | Purpose |
|---|---|
| `HUBSPOT_SERVICE_KEY` | Read-only HubSpot Service Key |
| `GOOGLE_CLIENT_SECRET` | Google OAuth web-client secret |
| `TOKEN_ENCRYPTION_KEY` | Random 32-byte-or-stronger secret used to encrypt the Google refresh token at rest |
| `SYNC_ADMIN_PASSWORD` | Strong unique password for the private setup/admin endpoints |

Worker variables (not secret unless noted):

| Variable | Purpose |
|---|---|
| `GOOGLE_CLIENT_ID` | Google OAuth web-client ID |
| `GOOGLE_REDIRECT_URI` | Exact Worker callback URL: `https://<worker-host>/oauth/google/callback` |
| `SYNC_ADMIN_USER` | HTTP Basic username; defaults to `calendar-admin` |
| `HUBSPOT_PORTAL_ID` | HubSpot portal ID; defaults to `149419802` |
| `HUBSPOT_TASKS_SEARCH_URL` | Optional supported API endpoint override; default is HubSpot 2026-09 |
| `DB` | D1 database binding |

Enable Google Calendar API in the Google Cloud project. Create a Web application OAuth client and register the exact callback URL above. The only Calendar scope requested is `https://www.googleapis.com/auth/calendar.events.owned` (event access on calendars the account owns); no read access to calendar settings, attendee lists, or other calendars is requested.

The Google refresh token is encrypted with AES-GCM before being written to the dedicated D1 database. OAuth state is single-use, expires after ten minutes, and uses PKCE. The app never returns token material from `/health`.

## One-time activation sequence

1. Create the new D1 database, apply `schema.sql`, and bind it as `DB`.
2. Set the secrets and variables above in Cloudflare. Do not paste tokens into chat or commit them.
3. Deploy the Worker to its own `workers.dev` hostname first. Do not add a custom domain, route or DNS change in this phase.
4. Open `/admin/google/start` in a browser and complete HTTP Basic authentication using the private admin credentials. Complete Google's consent screen once. The callback stores the refresh token encrypted.
5. Configure the HubSpot Service Key and confirm `/health` reports the two connections established.
6. POST `/admin/sync?mode=dry-run` with HTTP Basic authentication. Review the counts, source freshness and event sample. This does not write to Google Calendar.
7. Only after the dry-run result is acceptable, POST `/admin/sync?mode=apply`. This is the explicit first-write approval and is capped at 25 calendar events.
8. Configure Cron Trigger `*/15 * * * *`. Later runs reconcile changed and closed tasks, update existing source-owned events, and add new events.

The Worker stays fail-closed if the first sync has not been approved. It does not create events simply because credentials exist.

## Operations

- `GET /health`: connection state, source freshness, last run and error summary. No tokens or task bodies are returned.
- `GET /admin/google/start`: admin-authenticated Google OAuth start.
- `GET /oauth/google/callback`: Google OAuth callback (state/PKCE protected).
- `POST /admin/sync?mode=dry-run`: read sources and report a proposed sync without Google writes.
- `POST /admin/sync?mode=apply`: first owner-approved write (25-event cap).
- `POST /admin/sync?mode=continue`: authenticated manual continuation after first approval.
- Cron: automatic reconciliation every 15 minutes once first-run approval is recorded.

## Tests

Run the dependency-free domain tests from the repository root:

```sh
node --test workers/calendar-sync/tests/*.test.mjs
```

Integration tests against Google and HubSpot should use mock fetch adapters or test credentials in a non-production account. Never use a live send or HubSpot write to test this Worker; its only external write capability should be Google Calendar event management.
