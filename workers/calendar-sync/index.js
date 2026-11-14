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
const LOCK_TTL_SECONDS = 600;

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

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  })[character]);
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
  if (!env.STATE) missing.push("STATE");
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

function decodeBase64Url(value) {
  const base64 = String(value).replace(/-/g, "+").replace(/_/g, "/");
  const padded = base64 + "=".repeat((4 - base64.length % 4) % 4);
  const binary = atob(padded);
  return Uint8Array.from(binary, (character) => character.charCodeAt(0));
}

async function deriveAesKey(secret) {
  return crypto.subtle.importKey(
    "raw", await sha256(secret), { name: "AES-GCM" }, false, ["encrypt", "decrypt"]
  );
}

async function encryptSecret(value, secret) {
  const key = await deriveAesKey(secret);
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const ciphertext = await crypto.subtle.encrypt(
    { name: "AES-GCM", iv }, key, new TextEncoder().encode(value)
  );
  return { iv: base64Url(iv), ciphertext: base64Url(new Uint8Array(ciphertext)) };
}

async function decryptSecret(ciphertext, iv, secret) {
  const key = await deriveAesKey(secret);
  const plaintext = await crypto.subtle.decrypt(
    { name: "AES-GCM", iv: decodeBase64Url(iv) }, key, decodeBase64Url(ciphertext)
  );
  return new TextDecoder().decode(plaintext);
}

function randomSecret(bytes = 32) {
  return base64Url(crypto.getRandomValues(new Uint8Array(bytes)));
}

function decodeJwtPart(value) {
  return JSON.parse(new TextDecoder().decode(decodeBase64Url(value)));
}

async function verifyGitHubOidc(token) {
  const parts = String(token || "").split(".");
  if (parts.length !== 3) return { ok: false, reason: "malformed_token" };
  let header;
  let claims;
  try {
    header = decodeJwtPart(parts[0]);
    claims = decodeJwtPart(parts[1]);
  } catch {
    return { ok: false, reason: "malformed_token" };
  }

  if (header.alg !== "RS256" || !header.kid) return { ok: false, reason: "unsupported_signature" };
  if (claims.iss !== "https://token.actions.githubusercontent.com") return { ok: false, reason: "wrong_issuer" };
  const audience = claims.aud;
  if (!(audience === "cedwyn-hubspot-calendar-sync" ||
      (Array.isArray(audience) && audience.includes("cedwyn-hubspot-calendar-sync")))) {
    return { ok: false, reason: "wrong_audience" };
  }
  if (claims.repository !== "unclehowell/cedwyn-hubspot" ||
      claims.ref !== "refs/heads/main" ||
      !String(claims.workflow_ref || "").startsWith(
        "unclehowell/cedwyn-hubspot/.github/workflows/calendar-sync-scheduler.yml@refs/heads/main"
      ) ||
      !["schedule", "workflow_dispatch"].includes(claims.event_name)) {
    return { ok: false, reason: "workflow_not_authorized" };
  }

  const now = Math.floor(Date.now() / 1000);
  if (!Number.isFinite(Number(claims.exp)) || Number(claims.exp) <= now ||
      (claims.nbf != null && Number(claims.nbf) > now + 30) ||
      (claims.iat != null && Number(claims.iat) > now + 30)) {
    return { ok: false, reason: "expired_or_not_yet_valid" };
  }

  const jwksResponse = await fetch("https://token.actions.githubusercontent.com/.well-known/jwks", {
    cf: { cacheTtl: 3600, cacheEverything: true }
  });
  if (!jwksResponse.ok) return { ok: false, reason: "jwks_unavailable" };
  const jwks = await jwksResponse.json();
  const jwk = (jwks.keys || []).find((key) => key.kid === header.kid && key.kty === "RSA");
  if (!jwk) return { ok: false, reason: "signing_key_not_found" };

  const publicKey = await crypto.subtle.importKey(
    "jwk", jwk, { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" }, false, ["verify"]
  );
  const signingInput = new TextEncoder().encode(parts[0] + "." + parts[1]);
  const signature = decodeBase64Url(parts[2]);
  const valid = await crypto.subtle.verify("RSASSA-PKCS1-v1_5", publicKey, signature, signingInput);
  return valid ? { ok: true, claims } : { ok: false, reason: "invalid_signature" };
}

async function stateGet(env, key) {
  return env.STATE.get(key, "json");
}

async function statePut(env, key, value, options = undefined) {
  return env.STATE.put(key, JSON.stringify(value), options);
}

async function stateDelete(env, key) {
  return env.STATE.delete(key);
}

async function listAll(env, prefix) {
  const keys = [];
  let cursor;
  do {
    const page = await env.STATE.list({ prefix, ...(cursor ? { cursor } : {}), limit: 1000 });
    keys.push(...page.keys);
    cursor = page.list_complete ? undefined : page.cursor;
  } while (cursor);
  return keys;
}

async function metaGet(env, key) {
  const value = await stateGet(env, "meta/" + key);
  return value?.value ?? null;
}

async function metaPut(env, key, value) {
  await statePut(env, "meta/" + key, { value: String(value), updatedAt: new Date().toISOString() });
}

function eventStateKey(sourceType, sourceKey) {
  return "events/" + sourceType + "/" + encodeURIComponent(String(sourceKey));
}

async function startGoogleOAuth(request, env) {
  if (!env.GOOGLE_CLIENT_ID || !env.GOOGLE_CLIENT_SECRET || !env.GOOGLE_REDIRECT_URI ||
      !env.TOKEN_ENCRYPTION_KEY || !env.STATE) {
    return json({ ok: false, error: "Google OAuth / KV configuration is incomplete." }, 503);
  }

  const state = randomSecret(32);
  const verifier = randomSecret(48);
  const challenge = base64Url(await sha256(verifier));
  const stateHash = base64Url(await sha256(state));

  await statePut(env, "oauth/" + stateHash, {
    codeVerifier: verifier,
    expiresAt: Date.now() + 10 * 60 * 1000
  }, { expirationTtl: 600 });

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
  const stateKey = "oauth/" + stateHash;
  const stateRow = await stateGet(env, stateKey);
  await stateDelete(env, stateKey);
  if (!stateRow || Number(stateRow.expiresAt) < Date.now()) {
    return json({ ok: false, error: "OAuth state was missing, expired or already used." }, 400);
  }

  const form = new URLSearchParams({
    code,
    client_id: env.GOOGLE_CLIENT_ID,
    client_secret: env.GOOGLE_CLIENT_SECRET,
    redirect_uri: env.GOOGLE_REDIRECT_URI,
    grant_type: "authorization_code",
    code_verifier: stateRow.codeVerifier
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
  await statePut(env, "token/google", {
    refreshCiphertext: encrypted.ciphertext,
    refreshIv: encrypted.iv,
    calendarId: "primary",
    connectedAt: new Date().toISOString()
  });
  await metaPut(env, "google_connected", "true");

  return html("<!doctype html><meta name='viewport' content='width=device-width'>" +
    "<title>Google Calendar connected</title><main style='font:16px system-ui;max-width:680px;margin:3rem auto;padding:1rem'>" +
    "<h1>Google Calendar connected</h1><p>The one-time Google authorization succeeded. " +
    "No calendar events have been written yet.</p><p>Next: configure the HubSpot Service Key in Cloudflare, " +
    "run the dry-run preview, then approve the first sync.</p></main>");
}

async function getGoogleAccessToken(env) {
  const tokenRow = await stateGet(env, "token/google");
  if (!tokenRow) throw new Error("Google Calendar is not connected.");

  const refreshToken = await decryptSecret(
    tokenRow.refreshCiphertext, tokenRow.refreshIv, env.TOKEN_ENCRYPTION_KEY
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
    await statePut(env, "token/google", {
      ...tokenRow,
      refreshCiphertext: replacement.ciphertext,
      refreshIv: replacement.iv
    });
  }
  return data.access_token;
}

async function googleRequest(accessToken, calendarId, path, method = "GET", body = null) {
  const response = await fetch(
    "https://www.googleapis.com/calendar/v3/calendars/" +
    encodeURIComponent(calendarId) + "/" + path,
    {
      method,
      headers: {
        authorization: "Bearer " + accessToken,
        ...(body ? { "content-type": "application/json" } : {})
      },
      body: body ? JSON.stringify(body) : undefined
    }
  );
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
        filters: [{ propertyName: "hs_task_is_open", operator: "EQ", value: "true" }]
      }],
      properties: [
        "hs_task_subject", "hs_task_status", "hs_timestamp", "hs_task_priority",
        "hs_task_type", "hs_task_is_open", "hs_lastmodifieddate"
      ],
      limit: PAGE_SIZE,
      ...(after ? { after } : {})
    };
    const searchUrl = env.HUBSPOT_TASKS_SEARCH_URL ||
      "https://api.hubapi.com/crm/objects/2026-09/tasks/search";
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
    return buildEstateRoadmapPlan(await response.json().catch(() => null), nowMillis, 36);
  } catch (error) {
    console.warn("Estate roadmap feed unavailable; continuing with HubSpot only.", error.message);
    return { fresh: false, reason: "fetch_failed", events: [] };
  }
}

async function makeEventId(sourceType, sourceKey) {
  const digest = await sha256(sourceType + ":" + sourceKey);
  let hex = "";
  for (const byte of digest) hex += byte.toString(16).padStart(2, "0");
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
      private: { app: APP, sourceType: event.sourceType, sourceKey: event.sourceKey }
    }
  };
}

async function upsertCalendarEvent(env, accessToken, calendarId, event) {
  const eventId = await makeEventId(event.sourceType, event.sourceKey);
  const resource = eventResource(event, eventId);
  const hash = await contentHash(resource);
  const mappingKey = eventStateKey(event.sourceType, event.sourceKey);
  const mapping = await stateGet(env, mappingKey);
  let remote = await googleRequest(accessToken, calendarId, "events/" + eventId);

  if (remote) {
    const marker = remote.extendedProperties?.private || {};
    if (marker.app !== APP || marker.sourceType !== event.sourceType || marker.sourceKey !== event.sourceKey) {
      throw new Error("A Google event ID collision was detected; refusing to overwrite an unrelated event.");
    }
    if (mapping && mapping.contentHash === hash) return "unchanged";
    const patchResource = { ...resource };
    delete patchResource.id;
    await googleRequest(accessToken, calendarId, "events/" + eventId, "PATCH", patchResource);
  } else {
    try {
      await googleRequest(accessToken, calendarId, "events", "POST", resource);
    } catch (error) {
      // Concurrent retries may race to insert the same deterministic event ID.
      const raced = await googleRequest(accessToken, calendarId, "events/" + eventId);
      const marker = raced?.extendedProperties?.private || {};
      if (!raced || marker.app !== APP || marker.sourceType !== event.sourceType ||
          marker.sourceKey !== event.sourceKey) throw error;
      const patchResource = { ...resource };
      delete patchResource.id;
      await googleRequest(accessToken, calendarId, "events/" + eventId, "PATCH", patchResource);
      remote = raced;
    }
  }

  await statePut(env, mappingKey, {
    eventId, contentHash: hash,
    sourceMembers: event.sourceMembers || [],
    syncedAt: new Date().toISOString()
  });
  return remote ? "updated" : "created";
}

async function deleteCalendarEvent(env, accessToken, calendarId, sourceType, sourceKey, eventId) {
  const remote = await googleRequest(accessToken, calendarId, "events/" + encodeURIComponent(eventId));
  if (remote) {
    const marker = remote.extendedProperties?.private || {};
    if (marker.app !== APP || marker.sourceType !== sourceType || marker.sourceKey !== String(sourceKey)) {
      throw new Error("Refusing to delete an event without this sync service's source marker.");
    }
    await googleRequest(accessToken, calendarId, "events/" + encodeURIComponent(eventId), "DELETE");
  }
  await stateDelete(env, eventStateKey(sourceType, sourceKey));
}

async function acquireLock(env, runId) {
  const existing = await stateGet(env, "lock/sync");
  if (existing && Number(existing.leaseUntil) > Date.now()) return false;
  await statePut(env, "lock/sync", {
    owner: runId, leaseUntil: Date.now() + LOCK_TTL_SECONDS * 1000
  }, { expirationTtl: LOCK_TTL_SECONDS });
  return true;
}

async function releaseLock(env, runId) {
  const existing = await stateGet(env, "lock/sync");
  if (existing?.owner === runId) await stateDelete(env, "lock/sync");
}

async function createSyncPlan(env, nowMillis) {
  const tasks = await fetchAllHubSpotTasks(env);
  const portalId = env.HUBSPOT_PORTAL_ID || "149419802";
  const hubspotPlan = buildHubSpotPlan(tasks, nowMillis, portalId);
  const roadmapPlan = await fetchEstateRoadmap(nowMillis);
  return {
    tasks,
    hubspotPlan,
    roadmapPlan,
    events: hubspotPlan.events.concat(roadmapPlan.fresh ? roadmapPlan.events : [])
  };
}

async function previewSync(env) {
  const plan = await createSyncPlan(env, Date.now());
  const currentKeys = await listAll(env, "events/");
  const current = new Map();
  for (const item of currentKeys) {
    const mapping = await stateGet(env, item.name);
    if (mapping) current.set(item.name, mapping);
  }

  let newCount = 0;
  let changedCount = 0;
  let unchangedCount = 0;
  for (const event of plan.events) {
    const key = eventStateKey(event.sourceType, event.sourceKey);
    const mapping = current.get(key);
    if (!mapping) newCount++;
    else {
      const resource = eventResource(event, await makeEventId(event.sourceType, event.sourceKey));
      const hash = await contentHash(resource);
      if (mapping.contentHash === hash) unchangedCount++;
      else changedCount++;
    }
  }

  const desired = new Set(plan.events.map((event) => eventStateKey(event.sourceType, event.sourceKey)));
  const deletions = [];
  for (const [key, mapping] of current.entries()) {
    const split = key.split("/");
    const sourceType = split[1];
    const sourceKey = decodeURIComponent(split.slice(2).join("/"));
    if (sourceType === "hubspot_due_bundle") {
      const dueMillis = Number(sourceKey);
      if (Number.isFinite(dueMillis) && dueMillis > Date.now() && !desired.has(key)) {
        deletions.push({ sourceType, sourceKey });
      }
    } else if (sourceType === "estate_roadmap_day" && plan.roadmapPlan.fresh &&
               sourceKey >= localDateKey(Date.now()) && !desired.has(key)) {
      deletions.push({ sourceType, sourceKey });
    }
  }

  return {
    ok: true,
    mode: "dry-run",
    hubspot: {
      openTasks: plan.hubspotPlan.tasks.length,
      futureTasks: plan.hubspotPlan.futureTaskCount,
      futureCalendarBundles: plan.hubspotPlan.events.filter((e) => e.sourceType === "hubspot_due_bundle").length,
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
    plannedDeletes: deletions.length,
    sample: plan.events.slice(0, 12).map((event) => ({
      source: event.sourceType, sourceKey: event.sourceKey, summary: event.resource.summary
    })),
    note: "No Google Calendar writes were performed."
  };
}

async function runSync(env, limit = NORMAL_RUN_LIMIT) {
  const runId = randomSecret(16);
  if (!await acquireLock(env, runId)) return { ok: true, skipped: true, reason: "sync_lock_held" };

  const started = new Date().toISOString();
  try {
    const now = Date.now();
    const plan = await createSyncPlan(env, now);
    const tokenRow = await stateGet(env, "token/google");
    if (!tokenRow) throw new Error("Google Calendar is not connected.");
    const accessToken = await getGoogleAccessToken(env);
    const calendarId = tokenRow.calendarId || "primary";
    const batch = plan.events.slice(0, limit);
    const counts = { created: 0, updated: 0, unchanged: 0, deleted: 0 };

    for (const event of batch) {
      const result = await upsertCalendarEvent(env, accessToken, calendarId, event);
      counts[result]++;
    }

    const complete = batch.length === plan.events.length;
    if (complete) {
      const desiredFutureBundles = new Set(plan.hubspotPlan.events
        .filter((event) => event.sourceType === "hubspot_due_bundle").map((event) => String(event.sourceKey)));
      const desiredRoadmapDates = new Set(plan.roadmapPlan.fresh
        ? plan.roadmapPlan.events.map((event) => String(event.sourceKey)) : []);
      const eventKeys = await listAll(env, "events/");
      for (const item of eventKeys) {
        const mapping = await stateGet(env, item.name);
        if (!mapping) continue;
        const parts = item.name.split("/");
        const sourceType = parts[1];
        const sourceKey = decodeURIComponent(parts.slice(2).join("/"));
        if (sourceType === "hubspot_due_bundle") {
          const dueMillis = Number(sourceKey);
          if (Number.isFinite(dueMillis) && dueMillis > now && !desiredFutureBundles.has(sourceKey)) {
            await deleteCalendarEvent(env, accessToken, calendarId, sourceType, sourceKey, mapping.eventId);
            counts.deleted++;
          }
        } else if (sourceType === "estate_roadmap_day" && plan.roadmapPlan.fresh &&
            sourceKey >= localDateKey(now) && !desiredRoadmapDates.has(sourceKey)) {
          await deleteCalendarEvent(env, accessToken, calendarId, sourceType, sourceKey, mapping.eventId);
          counts.deleted++;
        }
      }
    }

    const result = {
      ok: true, runId, started, finished: new Date().toISOString(), complete, truncated: !complete,
      source: {
        hubspotOpenTasks: plan.hubspotPlan.tasks.length,
        futureTasks: plan.hubspotPlan.futureTaskCount,
        overdueActiveTasks: plan.hubspotPlan.overdueTaskCount,
        estateRoadmapStatus: plan.roadmapPlan.fresh ? "fresh" : "stale_or_unavailable",
        estateRoadmapGenerated: plan.roadmapPlan.generated || null
      },
      counts
    };
    await metaPut(env, "last_sync_at", result.finished);
    await metaPut(env, "last_sync_status", "ok");
    await metaPut(env, "last_sync_result", JSON.stringify(result));
    await metaPut(env, "estate_source_status", result.source.estateRoadmapStatus);
    await metaPut(env, "estate_source_generated", result.source.estateRoadmapGenerated || "");
    return result;
  } catch (error) {
    const result = {
      ok: false, runId, started, finished: new Date().toISOString(),
      error: error instanceof Error ? error.message : "Unknown sync error"
    };
    console.error("Calendar sync failed", result.error);
    await metaPut(env, "last_sync_at", result.finished);
    await metaPut(env, "last_sync_status", "error");
    await metaPut(env, "last_sync_error", result.error);
    return result;
  } finally {
    await releaseLock(env, runId);
  }
}

async function getHealth(env) {
  const missing = requiredConfiguration(env);
  const token = await stateGet(env, "token/google");
  const meta = {};
  for (const key of [
    "google_connected", "initial_sync_approved", "last_sync_at", "last_sync_status",
    "last_sync_result", "last_sync_error", "estate_source_status", "estate_source_generated"
  ]) meta[key] = await metaGet(env, key);

  return {
    ok: true,
    service: APP,
    mode: "one-way HubSpot → Google Calendar",
    cron: "*/15 * * * * (UTC trigger)",
    timeZone: TIME_ZONE,
    configured: missing.length === 0,
    missingConfiguration: missing,
    googleConnected: Boolean(token),
    firstSyncApproved: meta.initial_sync_approved === "true",
    lastSyncAt: meta.last_sync_at,
    lastSyncStatus: meta.last_sync_status,
    lastSyncError: meta.last_sync_error,
    estateSource: {
      status: meta.estate_source_status || "not_checked",
      generated: meta.estate_source_generated || null
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
  if (!env.STATE) minimum.push("STATE");
  if (!env.HUBSPOT_SERVICE_KEY) minimum.push("HUBSPOT_SERVICE_KEY");
  if (!env.SYNC_ADMIN_PASSWORD) minimum.push("SYNC_ADMIN_PASSWORD");
  if (minimum.length) return json({ ok: false, missingConfiguration: minimum }, 503);
  if (!isAdmin(request, env)) return authRequired();

  if (mode === "dry-run") {
    try { return json(await previewSync(env)); }
    catch (error) { return json({ ok: false, error: error.message }, 502); }
  }
  if (mode === "apply") {
    const missing = requiredConfiguration(env);
    if (missing.length) return json({ ok: false, missingConfiguration: missing }, 503);
    const token = await stateGet(env, "token/google");
    if (!token) return json({ ok: false, error: "Connect Google Calendar first at /admin/google/start." }, 409);
    await metaPut(env, "initial_sync_approved", "true");
    return json({ ...(await runSync(env, FIRST_RUN_LIMIT)), firstRunLimit: FIRST_RUN_LIMIT });
  }
  if (mode === "continue") {
    if (await metaGet(env, "initial_sync_approved") !== "true") {
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
      catch { return json({ ok: false, error: "KV state binding unavailable." }, 503); }
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
      return initialize(request, env);
    }
    if (url.pathname === "/internal/scheduled" && request.method === "POST") {
      const authorization = request.headers.get("authorization") || "";
      const match = /^Bearer\\s+(.+)$/.exec(authorization);
      if (!match) return json({ ok: false, error: "GitHub OIDC token required." }, 401);
      const verified = await verifyGitHubOidc(match[1]);
      if (!verified.ok) return json({ ok: false, error: "Scheduler identity rejected.", reason: verified.reason }, 403);
      if (await metaGet(env, "initial_sync_approved") !== "true") {
        return json({ ok: true, skipped: true, reason: "first_sync_not_approved" });
      }
      const result = await runSync(env, NORMAL_RUN_LIMIT);
      return json(result, result.ok ? 200 : 502);
    }
    return json({ ok: false, error: "Not found" }, 404);
  },

  async scheduled(controller, env) {
    if (await metaGet(env, "initial_sync_approved") !== "true") {
      console.log("Calendar sync skipped: first sync awaits owner approval.");
      return;
    }
    const result = await runSync(env, NORMAL_RUN_LIMIT);
    if (!result.ok) throw new Error(result.error || "Calendar sync failed.");
  }
};
