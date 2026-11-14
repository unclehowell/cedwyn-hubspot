import {
  buildEstateRoadmapPlan,
  buildHubSpotPlan,
  localDateKey
} from "./domain.js";

const APP = "cedwyn-hubspot-calendar-sync";
const TIME_ZONE = "Europe/Amsterdam";
const GOOGLE_SCOPE = "https://www.googleapis.com/auth/calendar.events.owned";
const ROADMAP_URL = "https://raw.githubusercontent.com/unclehowell/cedwyn-dartboard/main/public/data/roadmap.json";
const MAX_HUBSPOT_PAGES = 100;
const PAGE_SIZE = 100;
const FIRST_RUN_LIMIT = 25;
const NORMAL_RUN_LIMIT = 250;
const LOCK_MS = 10 * 60 * 1000;

function json(data, status = 200) {
  return new Response(JSON.stringify(data, null, 2), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store, max-age=0",
      "x-content-type-options": "nosniff",
      "x-robots-tag": "noindex, nofollow"
    }
  });
}

function html(body, status = 200) {
  return new Response(body, {
    status,
    headers: {
      "content-type": "text/html; charset=utf-8",
      "cache-control": "no-store, max-age=0",
      "x-content-type-options": "nosniff",
      "x-robots-tag": "noindex, nofollow",
      "content-security-policy": "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; frame-ancestors 'none'"
    }
  });
}

function basicCredentials(request) {
  const header = request.headers.get("authorization") || "";
  if (!header.startsWith("Basic ")) return null;
  try {
    const decoded = atob(header.slice(6));
    const index = decoded.indexOf(":");
    if (index < 0) return null;
    return { user: decoded.slice(0, index), password: decoded.slice(index + 1) };
  } catch {
    return null;
  }
}

function safeEqual(left, right) {
  const a = new TextEncoder().encode(String(left || ""));
  const b = new TextEncoder().encode(String(right || ""));
  let diff = a.length ^ b.length;
  const length = Math.max(a.length, b.length);
  for (let i = 0; i < length; i++) diff |= (a[i] || 0) ^ (b[i] || 0);
  return diff === 0;
}

function isAdmin(request, env) {
  if (!env.SYNC_ADMIN_PASSWORD) return false;
  const credentials = basicCredentials(request);
  if (!credentials) return false;
  const expectedUser = env.SYNC_ADMIN_USER || "calendar-admin";
  return safeEqual(credentials.user, expectedUser) &&
    safeEqual(credentials.password, env.SYNC_ADMIN_PASSWORD);
}

function authRequired() {
  return new Response("Authentication required", {
    status: 401,
    headers: {
      "www-authenticate": 'Basic realm="Calendar sync setup", charset="UTF-8"',
      "cache-control": "no-store",
      "x-robots-tag": "noindex, nofollow"
    }
  });
}

function requiredConfiguration(env) {
  const missing = [];
  for (const key of ["HUBSPOT_SERVICE_KEY", "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET",
    "GOOGLE_REDIRECT_URI", "TOKEN_ENCRYPTION_KEY", "SYNC_ADMIN_PASSWORD"]) {
    if (!env[key]) missing.push(key);
  }
  if (!env.DB) missing.push("DB");
  return missing;
}

async function sha256(value) {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(String(value)));
  return new Uint8Array(digest);
}

function base64Url(bytes) {
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

async function deriveAesKey(secret) {
  const raw = await sha256(secret);
  return crypto.subtle.importKey("raw", raw, { name: "AES-GCM" }, false, ["encrypt", "decrypt"]);
}

async function encryptSecret(value, secret) {
  const key = await deriveAesKey(secret);
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const ciphertext = await crypto.subtle.encrypt(
    { name: "AES-GCM", iv },
    key,
    new TextEncoder().encode(value)
  );
  return { iv: base64Url(iv), ciphertext: base64Url(new Uint8Array(ciphertext)) };
}

function decodeBase64Url(value) {
  const base64 = String(value).replace(/-/g, "+").replace(/_/g, "/");
  const padded = base64 + "=".repeat((4 - base64.length % 4) % 4);
  const binary = atob(padded);
  return Uint8Array.from(binary, (character) => character.charCodeAt(0));
}

async function decryptSecret(ciphertext, iv, secret) {
  const key = await deriveAesKey(secret);
  const plaintext = await crypto.subtle.decrypt(
    { name: "AES-GCM", iv: decodeBase64Url(iv) },
    key,
    decodeBase64Url(ciphertext)
  );
  return new TextDecoder().decode(plaintext);
}

function randomSecret(bytes = 32) {
  return base64Url(crypto.getRandomValues(new Uint8Array(bytes)));
}

async function getMeta(db, key) {
  const row = await db.prepare("SELECT value FROM cal_sync_meta WHERE key = ?").bind(key).first();
  return row?.value ?? null;
}

async function putMeta(db, key, value) {
  await db.prepare(
    "INSERT INTO cal_sync_meta (key, value, updated_at) VALUES (?, ?, ?) " +
    "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at"
  ).bind(key, String(value), new Date().toISOString()).run();
}

async function startGoogleOAuth(request, env) {
  if (!env.GOOGLE_CLIENT_ID || !env.GOOGLE_CLIENT_SECRET || !env.GOOGLE_REDIRECT_URI ||
      !env.TOKEN_ENCRYPTION_KEY || !env.DB) {
    return json({ ok: false, error: "Google OAuth / D1 configuration is incomplete." }, 503);
  }

  const state = randomSecret(32);
  const verifier = randomSecret(48);
  const challenge = base64Url(await sha256(verifier));
  const stateHash = base64Url(await sha256(state));
  const now = Date.now();

  await env.DB.prepare("DELETE FROM cal_oauth_states WHERE expires_at < ?").bind(now).run();
  await env.DB.prepare(
    "INSERT INTO cal_oauth_states (state_hash, code_verifier, created_at, expires_at) VALUES (?, ?, ?, ?)"
  ).bind(stateHash, verifier, now, now + 10 * 60 * 1000).run();

  const url = new URL("https://accounts.google.com/o/oauth2/v2/auth");
  url.searchParams.set("client_id", env.GOOGLE_CLIENT_ID);
  url.searchParams.set("redirect_uri", env.GOOGLE_REDIRECT_URI);
  url.searchParams.set("response_type", "code");
  url.searchParams.set("scope", GOOGLE_SCOPE);
  url.searchParams.set("access_type", "offline");
  url.searchParams.set("prompt", "consent");
  url.searchParams.set("include_granted_scopes", "true");
  url.searchParams.set("state", state);
  url.searchParams.set("code_challenge", challenge);
  url.searchParams.set("code_challenge_method", "S256");

  return Response.redirect(url.toString(), 302);
}

async function handleGoogleCallback(request, env) {
  const url = new URL(request.url);
  const providerError = url.searchParams.get("error");
  if (providerError) {
    return html("<h1>Google Calendar was not connected</h1><p>" +
      escapeHtml(providerError) + "</p>", 400);
  }

  const code = url.searchParams.get("code");
  const state = url.searchParams.get("state");
  if (!code || !state) return json({ ok: false, error: "Missing OAuth code or state." }, 400);

  const stateHash = base64Url(await sha256(state));
  const stateRow = await env.DB.prepare(
    "SELECT code_verifier, expires_at FROM cal_oauth_states WHERE state_hash = ?"
  ).bind(stateHash).first();

  // Single-use state: consume before exchanging the code.
  await env.DB.prepare("DELETE FROM cal_oauth_states WHERE state_hash = ?").bind(stateHash).run();
  if (!stateRow || Number(stateRow.expires_at) < Date.now()) {
    return json({ ok: false, error: "OAuth state was missing, expired or already used." }, 400);
  }

  const form = new URLSearchParams({
    code,
    client_id: env.GOOGLE_CLIENT_ID,
    client_secret: env.GOOGLE_CLIENT_SECRET,
    redirect_uri: env.GOOGLE_REDIRECT_URI,
    grant_type: "authorization_code",
    code_verifier: stateRow.code_verifier
  });
  const tokenResponse = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "content-type": "application/x-www-form-urlencoded" },
    body: form
  });
  const tokenData = await tokenResponse.json().catch(() => ({}));
  if (!tokenResponse.ok) {
    console.error("Google OAuth exchange failed", tokenResponse.status, tokenData.error);
    return json({ ok: false, error: "Google OAuth token exchange failed.", status: tokenResponse.status }, 502);
  }
  if (!tokenData.refresh_token) {
    return json({
      ok: false,
      error: "Google did not return an offline refresh token. Revoke the previous grant and reconnect with consent."
    }, 409);
  }

  const encrypted = await encryptSecret(tokenData.refresh_token, env.TOKEN_ENCRYPTION_KEY);
  await env.DB.prepare(
    "INSERT INTO cal_sync_tokens (id, refresh_ciphertext, refresh_iv, calendar_id, connected_at) " +
    "VALUES ('google', ?, ?, 'primary', ?) " +
    "ON CONFLICT(id) DO UPDATE SET refresh_ciphertext=excluded.refresh_ciphertext, " +
    "refresh_iv=excluded.refresh_iv, calendar_id='primary', connected_at=excluded.connected_at"
  ).bind(encrypted.ciphertext, encrypted.iv, new Date().toISOString()).run();

  await putMeta(env.DB, "google_connected", "true");
  return html("<!doctype html><meta name='viewport' content='width=device-width'>" +
    "<title>Google Calendar connected</title><main style='font:16px system-ui;max-width:680px;margin:3rem auto;padding:1rem'>" +
    "<h1>Google Calendar connected</h1><p>The one-time Google authorization succeeded. " +
    "No calendar events have been written yet.</p><p>Next: configure the HubSpot Service Key in Cloudflare, " +
    "run the dry-run preview, then approve the first sync.</p></main>");
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  })[character]);
}

async function getGoogleAccessToken(env) {
  const tokenRow = await env.DB.prepare(
    "SELECT refresh_ciphertext, refresh_iv FROM cal_sync_tokens WHERE id='google'"
  ).first();
  if (!tokenRow) throw new Error("Google Calendar is not connected.");

  const refreshToken = await decryptSecret(
    tokenRow.refresh_ciphertext, tokenRow.refresh_iv, env.TOKEN_ENCRYPTION_KEY
  );
  const form = new URLSearchParams({
    client_id: env.GOOGLE_CLIENT_ID,
    client_secret: env.GOOGLE_CLIENT_SECRET,
    refresh_token: refreshToken,
    grant_type: "refresh_token"
  });
  const response = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "content-type": "application/x-www-form-urlencoded" },
    body: form
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok || !data.access_token) {
    console.error("Google refresh failed", response.status, data.error);
    throw new Error("Google access-token refresh failed; reconnect Google Calendar.");
  }

  if (data.refresh_token) {
    const replacement = await encryptSecret(data.refresh_token, env.TOKEN_ENCRYPTION_KEY);
    await env.DB.prepare(
      "UPDATE cal_sync_tokens SET refresh_ciphertext=?, refresh_iv=? WHERE id='google'"
    ).bind(replacement.ciphertext, replacement.iv).run();
  }
  return data.access_token;
}

async function googleRequest(accessToken, path, method = "GET", body = null) {
  const response = await fetch("https://www.googleapis.com/calendar/v3/calendars/primary/" + path, {
    method,
    headers: {
      authorization: "Bearer " + accessToken,
      ...(body ? { "content-type": "application/json" } : {})
    },
    body: body ? JSON.stringify(body) : undefined
  });
  if (response.status === 404 && (method === "GET" || method === "DELETE")) return null;
  if (response.status === 204) return null;
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    console.error("Google Calendar API error", method, path, response.status, data.error?.code);
    throw new Error("Google Calendar API request failed with status " + response.status + ".");
  }
  return data;
}

async function fetchAllHubSpotTasks(env) {
  if (!env.HUBSPOT_SERVICE_KEY) throw new Error("HubSpot Service Key is not configured.");
  const all = [];
  let after = null;
  for (let page = 0; page < MAX_HUBSPOT_PAGES; page++) {
    const payload = {
      filterGroups: [{
        filters: [{
          propertyName: "hs_task_is_open",
          operator: "EQ",
          value: "true"
        }]
      }],
      properties: [
        "hs_task_subject",
        "hs_task_status",
        "hs_timestamp",
        "hs_task_priority",
        "hs_task_type",
        "hs_task_is_open",
        "hs_lastmodifieddate"
      ],
      limit: PAGE_SIZE,
      ...(after ? { after } : {})
    };
    const searchUrl = env.HUBSPOT_TASKS_SEARCH_URL || "https://api.hubapi.com/crm/objects/2026-09/tasks/search";
    const response = await fetch(searchUrl, {
      method: "POST",
      headers: {
        authorization: "Bearer " + env.HUBSPOT_SERVICE_KEY,
        "content-type": "application/json"
      },
      body: JSON.stringify(payload)
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      console.error("HubSpot task search failed", response.status, data.category || data.status);
      throw new Error("HubSpot task search failed with status " + response.status + ".");
    }
    all.push(...(data.results || []));
    after = data.paging?.next?.after || null;
    if (!after) return all;
  }
  throw new Error("HubSpot task pagination exceeded the safety limit; no calendar changes were made.");
}

async function fetchEstateRoadmap(nowMillis) {
  try {
    const response = await fetch(ROADMAP_URL, {
      headers: { accept: "application/json", "cache-control": "no-cache" },
      cache: "no-store"
    });
    if (!response.ok) return { fresh: false, reason: "http_" + response.status, events: [] };
    const roadmap = await response.json().catch(() => null);
    return buildEstateRoadmapPlan(roadmap, nowMillis, 36);
  } catch (error) {
    console.warn("Estate roadmap feed unavailable; continuing with HubSpot only.", error.message);
    return { fresh: false, reason: "fetch_failed", events: [] };
  }
}

async function makeEventId(sourceType, sourceKey) {
  const value = sourceType + ":" + sourceKey;
  const digest = await sha256(value);
  let hex = "";
  for (const byte of digest) hex += byte.toString(16).padStart(2, "0");
  // Google Calendar custom IDs use lowercase base32hex characters; hex is a valid subset.
  return hex.slice(0, 32);
}

async function contentHash(resource) {
  return base64Url(await sha256(JSON.stringify(resource)));
}

function eventResource(event, eventId) {
  return {
    id: eventId,
    ...event.resource,
    extendedProperties: {
      private: {
        app: APP,
        sourceType: event.sourceType,
        sourceKey: event.sourceKey
      }
    }
  };
}

async function upsertCalendarEvent(env, accessToken, event) {
  const eventId = await makeEventId(event.sourceType, event.sourceKey);
  const resource = eventResource(event, eventId);
  const hash = await contentHash(resource);
  const mapping = await env.DB.prepare(
    "SELECT event_id, content_hash FROM cal_sync_events WHERE source_type=? AND source_key=?"
  ).bind(event.sourceType, event.sourceKey).first();

  let remote = await googleRequest(accessToken, "events/" + eventId);
  if (remote) {
    const marker = remote.extendedProperties?.private || {};
    if (marker.app !== APP || marker.sourceType !== event.sourceType || marker.sourceKey !== event.sourceKey) {
      throw new Error("A Google event ID collision was detected; refusing to overwrite an unrelated event.");
    }
    if (mapping && mapping.content_hash === hash) return "unchanged";
    const patchResource = { ...resource };
    delete patchResource.id;
    await googleRequest(accessToken, "events/" + eventId, "PATCH", patchResource);
  } else {
    await googleRequest(accessToken, "events", "POST", resource);
  }

  await env.DB.prepare(
    "INSERT INTO cal_sync_events (source_type, source_key, event_id, content_hash, source_members_json, synced_at) " +
    "VALUES (?, ?, ?, ?, ?, ?) " +
    "ON CONFLICT(source_type, source_key) DO UPDATE SET event_id=excluded.event_id, " +
    "content_hash=excluded.content_hash, source_members_json=excluded.source_members_json, synced_at=excluded.synced_at"
  ).bind(
    event.sourceType,
    event.sourceKey,
    eventId,
    hash,
    JSON.stringify(event.sourceMembers || []),
    new Date().toISOString()
  ).run();
  return remote ? "updated" : "created";
}

async function deleteCalendarEvent(env, accessToken, row) {
  const remote = await googleRequest(accessToken, "events/" + encodeURIComponent(row.event_id));
  if (remote) {
    const marker = remote.extendedProperties?.private || {};
    if (marker.app !== APP || marker.sourceType !== row.source_type || marker.sourceKey !== row.source_key) {
      throw new Error("Refusing to delete an event without this sync service's source marker.");
    }
    await googleRequest(accessToken, "events/" + encodeURIComponent(row.event_id), "DELETE");
  }
  await env.DB.prepare(
    "DELETE FROM cal_sync_events WHERE source_type=? AND source_key=?"
  ).bind(row.source_type, row.source_key).run();
}

async function acquireLock(env, runId) {
  const now = Date.now();
  const result = await env.DB.prepare(
    "UPDATE cal_sync_lock SET owner=?, lease_until=? WHERE id='sync' AND lease_until < ?"
  ).bind(runId, now + LOCK_MS, now).run();
  return Number(result.meta?.changes || 0) === 1;
}

async function releaseLock(env, runId) {
  await env.DB.prepare(
    "UPDATE cal_sync_lock SET owner=NULL, lease_until=0 WHERE id='sync' AND owner=?"
  ).bind(runId).run();
}

async function createSyncPlan(env, nowMillis) {
  const tasks = await fetchAllHubSpotTasks(env);
  const portalId = env.HUBSPOT_PORTAL_ID || "149419802";
  const hubspotPlan = buildHubSpotPlan(tasks, nowMillis, portalId);
  const roadmapPlan = await fetchEstateRoadmap(nowMillis);
  const events = hubspotPlan.events.concat(roadmapPlan.fresh ? roadmapPlan.events : []);
  return { tasks, hubspotPlan, roadmapPlan, events };
}

async function previewSync(env) {
  const plan = await createSyncPlan(env, Date.now());
  const rows = await env.DB.prepare(
    "SELECT source_type, source_key, content_hash FROM cal_sync_events"
  ).all();
  const current = new Map((rows.results || []).map((row) =>
    [row.source_type + "|" + row.source_key, row.content_hash]
  ));
  let newCount = 0;
  let changedCount = 0;
  let unchangedCount = 0;
  for (const event of plan.events) {
    const key = event.sourceType + "|" + event.sourceKey;
    if (!current.has(key)) newCount++;
    else {
      const resource = eventResource(event, await makeEventId(event.sourceType, event.sourceKey));
      const hash = await contentHash(resource);
      if (current.get(key) === hash) unchangedCount++;
      else changedCount++;
    }
  }
  return {
    ok: true,
    mode: "dry-run",
    hubspot: {
      openTasks: plan.hubspotPlan.tasks.length,
      futureTasks: plan.hubspotPlan.futureTaskCount,
      futureCalendarBundles: plan.hubspotPlan.events.filter((event) => event.sourceType === "hubspot_due_bundle").length,
      overdueActiveTasks: plan.hubspotPlan.overdueTaskCount,
      deferredPastDue: plan.hubspotPlan.deferredPastDueCount,
      untimedOpenTasks: plan.hubspotPlan.untimedTaskCount
    },
    estate: {
      status: plan.roadmapPlan.fresh ? "fresh" : "stale_or_unavailable",
      reason: plan.roadmapPlan.reason || null,
      generated: plan.roadmapPlan.generated || null,
      ageHours: plan.roadmapPlan.ageHours ?? null,
      calendarDays: plan.roadmapPlan.events.length
    },
    plannedEvents: plan.events.length,
    newEvents: newCount,
    changedEvents: changedCount,
    unchangedEvents: unchangedCount,
    sample: plan.events.slice(0, 12).map((event) => ({
      source: event.sourceType,
      sourceKey: event.sourceKey,
      summary: event.resource.summary
    })),
    note: "No Google Calendar writes were performed."
  };
}

async function runSync(env, limit = NORMAL_RUN_LIMIT) {
  const runId = randomSecret(16);
  if (!await acquireLock(env, runId)) {
    return { ok: true, skipped: true, reason: "sync_lock_held" };
  }

  const started = new Date().toISOString();
  try {
    const now = Date.now();
    const plan = await createSyncPlan(env, now);
    const accessToken = await getGoogleAccessToken(env);
    const batch = plan.events.slice(0, limit);
    const counts = { created: 0, updated: 0, unchanged: 0, deleted: 0 };
    for (const event of batch) {
      const result = await upsertCalendarEvent(env, accessToken, event);
      counts[result]++;
    }

    const isComplete = batch.length === plan.events.length;
    if (isComplete) {
      const desiredFutureBundles = new Set(plan.hubspotPlan.events
        .filter((event) => event.sourceType === "hubspot_due_bundle")
        .map((event) => event.sourceKey));
      const desiredRoadmapDates = new Set(plan.roadmapPlan.fresh
        ? plan.roadmapPlan.events.map((event) => event.sourceKey)
        : []);
      const activeIds = plan.hubspotPlan.activeTaskIds;
      const mappings = await env.DB.prepare("SELECT * FROM cal_sync_events").all();

      for (const row of mappings.results || []) {
        if (row.source_type === "hubspot_due_bundle") {
          const dueMillis = Number(row.source_key);
          // Keep past-due reminders as calendar history. Future groups disappear only
          // when every member is no longer open or their due time has been changed.
          if (Number.isFinite(dueMillis) && dueMillis > now && !desiredFutureBundles.has(row.source_key)) {
            await deleteCalendarEvent(env, accessToken, row);
            counts.deleted++;
          }
        } else if (row.source_type === "estate_roadmap_day" && plan.roadmapPlan.fresh &&
            row.source_key >= localDateKey(now) && !desiredRoadmapDates.has(row.source_key)) {
          await deleteCalendarEvent(env, accessToken, row);
          counts.deleted++;
        }
      }
    }

    const result = {
      ok: true,
      runId,
      started,
      finished: new Date().toISOString(),
      complete: isComplete,
      truncated: !isComplete,
      source: {
        hubspotOpenTasks: plan.hubspotPlan.tasks.length,
        futureTasks: plan.hubspotPlan.futureTaskCount,
        overdueActiveTasks: plan.hubspotPlan.overdueTaskCount,
        estateRoadmapStatus: plan.roadmapPlan.fresh ? "fresh" : "stale_or_unavailable",
        estateRoadmapGenerated: plan.roadmapPlan.generated || null
      },
      counts
    };
    await putMeta(env.DB, "last_sync_at", result.finished);
    await putMeta(env.DB, "last_sync_status", "ok");
    await putMeta(env.DB, "last_sync_result", JSON.stringify(result));
    await putMeta(env.DB, "estate_source_status", plan.roadmapPlan.fresh ? "fresh" : "stale_or_unavailable");
    await putMeta(env.DB, "estate_source_generated", plan.roadmapPlan.generated || "");
    return result;
  } catch (error) {
    const result = {
      ok: false,
      runId,
      started,
      finished: new Date().toISOString(),
      error: error instanceof Error ? error.message : "Unknown sync error"
    };
    console.error("Calendar sync failed", result.error);
    await putMeta(env.DB, "last_sync_at", result.finished);
    await putMeta(env.DB, "last_sync_status", "error");
    await putMeta(env.DB, "last_sync_error", result.error);
    return result;
  } finally {
    await releaseLock(env, runId);
  }
}

async function getHealth(env) {
  const keys = [
    "google_connected",
    "initial_sync_approved",
    "last_sync_at",
    "last_sync_status",
    "last_sync_result",
    "last_sync_error",
    "estate_source_status",
    "estate_source_generated"
  ];
  const values = {};
  for (const key of keys) values[key] = await getMeta(env.DB, key);
  const missing = requiredConfiguration(env);
  const token = await env.DB.prepare("SELECT connected_at FROM cal_sync_tokens WHERE id='google'").first();
  return {
    ok: true,
    service: APP,
    mode: "one-way HubSpot → Google Calendar",
    cron: "*/15 * * * *",
    timeZone: TIME_ZONE,
    configured: missing.length === 0,
    missingConfiguration: missing,
    googleConnected: Boolean(token),
    firstSyncApproved: values.initial_sync_approved === "true",
    lastSyncAt: values.last_sync_at,
    lastSyncStatus: values.last_sync_status,
    lastSyncError: values.last_sync_error,
    estateSource: {
      status: values.estate_source_status || "not_checked",
      generated: values.estate_source_generated || null
    },
    guardrails: [
      "HubSpot is the source of truth; this Worker never writes to HubSpot.",
      "Calendar events are private and source-marked; only this Worker's own events may be changed or deleted.",
      "Task bodies and email contents are never copied."
    ]
  };
}

async function initialize(request, env) {
  const mode = new URL(request.url).searchParams.get("mode") || "dry-run";
  const minimum = [];
  if (!env.DB) minimum.push("DB");
  if (!env.HUBSPOT_SERVICE_KEY) minimum.push("HUBSPOT_SERVICE_KEY");
  if (!env.SYNC_ADMIN_PASSWORD) minimum.push("SYNC_ADMIN_PASSWORD");
  if (minimum.length) return json({ ok: false, missingConfiguration: minimum }, 503);
  if (!isAdmin(request, env)) return authRequired();

  if (mode === "dry-run") {
    try {
      return json(await previewSync(env));
    } catch (error) {
      return json({ ok: false, error: error.message }, 502);
    }
  }
  if (mode === "apply") {
    const missing = requiredConfiguration(env);
    if (missing.length) return json({ ok: false, missingConfiguration: missing }, 503);
    const token = await env.DB.prepare("SELECT id FROM cal_sync_tokens WHERE id='google'").first();
    if (!token) return json({ ok: false, error: "Connect Google Calendar first at /admin/google/start." }, 409);
    await putMeta(env.DB, "initial_sync_approved", "true");
    const result = await runSync(env, FIRST_RUN_LIMIT);
    return json({ ...result, firstRunLimit: FIRST_RUN_LIMIT });
  }
  if (mode === "continue") {
    if (await getMeta(env.DB, "initial_sync_approved") !== "true") {
      return json({ ok: false, error: "The first sync has not been approved." }, 409);
    }
    return json(await runSync(env, NORMAL_RUN_LIMIT));
  }
  return json({ ok: false, error: "Unknown sync mode." }, 400);
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === "/health" && request.method === "GET") {
      try { return json(await getHealth(env)); }
      catch (error) { return json({ ok: false, error: "Database not initialized or unavailable." }, 503); }
    }

    if (url.pathname === "/admin/google/start" && request.method === "GET") {
      if (!isAdmin(request, env)) return authRequired();
      try { return await startGoogleOAuth(request, env); }
      catch (error) { return json({ ok: false, error: "Unable to start Google OAuth." }, 503); }
    }

    if (url.pathname === "/oauth/google/callback" && request.method === "GET") {
      try { return await handleGoogleCallback(request, env); }
      catch (error) {
        console.error("Google callback failed", error.message);
        return json({ ok: false, error: "Google Calendar connection failed." }, 502);
      }
    }

    if (url.pathname === "/admin/sync" && request.method === "POST") {
      if (!isAdmin(request, env)) return authRequired();
      return initialize(request, env);
    }

    return json({ ok: false, error: "Not found" }, 404);
  },

  async scheduled(controller, env) {
    if (await getMeta(env.DB, "initial_sync_approved") !== "true") {
      console.log("Calendar sync skipped: first sync awaits owner approval.");
      return;
    }
    const result = await runSync(env, NORMAL_RUN_LIMIT);
    if (!result.ok) throw new Error(result.error || "Calendar sync failed.");
  }
};
