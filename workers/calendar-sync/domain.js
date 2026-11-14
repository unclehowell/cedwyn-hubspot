export const TIME_ZONE = "Europe/Amsterdam";
export const OVERDUE_STATUSES = new Set(["NOT_STARTED", "IN_PROGRESS", "WAITING"]);
export const PRIORITY_ORDER = { HIGH: 0, MEDIUM: 1, LOW: 2, NONE: 3 };

export function parseHubSpotTimestamp(value) {
  if (value == null || value === "") return null;
  const numeric = Number(value);
  const millis = Number.isFinite(numeric) && numeric > 0
    ? (numeric < 100000000000 ? numeric * 1000 : numeric)
    : Date.parse(String(value));
  return Number.isFinite(millis) ? millis : null;
}

export function localDateKey(value, timeZone = TIME_ZONE) {
  const date = value instanceof Date ? value : new Date(value);
  if (!Number.isFinite(date.getTime())) throw new TypeError("Invalid date");
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone, year: "numeric", month: "2-digit", day: "2-digit"
  }).formatToParts(date);
  const part = (type) => parts.find((item) => item.type === type)?.value;
  return part("year") + "-" + part("month") + "-" + part("day");
}

export function nextDateKey(dateKey) {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(dateKey);
  if (!match) throw new TypeError("Invalid date key");
  const date = new Date(Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3]) + 1));
  return date.toISOString().slice(0, 10);
}

export function makeLocalTimedRange(dateKey, hour, minute, durationMinutes = 15) {
  const pad = (n) => String(n).padStart(2, "0");
  const start = dateKey + "T" + pad(hour) + ":" + pad(minute) + ":00";
  const endDate = new Date(Date.UTC(
    Number(dateKey.slice(0, 4)),
    Number(dateKey.slice(5, 7)) - 1,
    Number(dateKey.slice(8, 10)),
    hour,
    minute + durationMinutes
  ));
  const end = endDate.toISOString().slice(0, 16) + ":00";
  return {
    start: { dateTime: start, timeZone: TIME_ZONE },
    end: { dateTime: end, timeZone: TIME_ZONE }
  };
}

export function normalizeTask(task) {
  const p = task?.properties || {};
  const id = String(task?.id || task?.hs_object_id || "").trim();
  const due = parseHubSpotTimestamp(p.hs_timestamp);
  if (!id) return null;
  return {
    id,
    title: String(p.hs_task_subject || "Untitled HubSpot task").trim().slice(0, 180),
    status: String(p.hs_task_status || "UNKNOWN").toUpperCase(),
    priority: String(p.hs_task_priority || "NONE").toUpperCase(),
    type: String(p.hs_task_type || "TODO").toUpperCase(),
    due,
    isOpen: p.hs_task_is_open == null ? true : String(p.hs_task_is_open).toLowerCase() === "true"
  };
}

function hubSpotTaskUrl(portalId, taskId) {
  return "https://app.hubspot.com/tasks/" + encodeURIComponent(portalId) +
    "/view/all/task/" + encodeURIComponent(taskId) +
    "?utm_source=cedwyn_calendar_sync&utm_medium=calendar_event";
}

function priorityOrder(task) {
  return PRIORITY_ORDER[task.priority] ?? 4;
}

function renderTaskLine(task, portalId) {
  return "- " + task.title + " [" + task.status + " / " + task.priority + "] (task " +
    task.id + ")\n  " + hubSpotTaskUrl(portalId, task.id);
}

export function buildHubSpotPlan(rawTasks, nowMillis, portalId) {
  const tasks = rawTasks.map(normalizeTask).filter((task) => task && task.isOpen);
  const groups = new Map();
  const overdue = [];
  let untimed = 0;

  for (const task of tasks) {
    if (task.due == null) {
      untimed++;
      continue;
    }
    if (task.due > nowMillis) {
      const key = String(task.due);
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(task);
    } else if (OVERDUE_STATUSES.has(task.status)) {
      overdue.push(task);
    }
  }

  const events = [];
  for (const [sourceKey, members] of groups.entries()) {
    members.sort((a, b) => priorityOrder(a) - priorityOrder(b) || a.title.localeCompare(b.title));
    const due = Number(sourceKey);
    const start = new Date(due).toISOString();
    const end = new Date(due + 15 * 60 * 1000).toISOString();
    const count = members.length;
    const title = count === 1 ? members[0].title : "HubSpot: " + count + " tasks due";
    const description = [
      "Automatically maintained from HubSpot. HubSpot remains the source of truth.",
      "Due: " + start + " (" + TIME_ZONE + ")",
      "This is a reminder bundle; open the HubSpot task links for current details.",
      "",
      ...members.slice(0, 60).map((task) => renderTaskLine(task, portalId)),
      ...(members.length > 60 ? ["\n+" + (members.length - 60) + " more task(s) in HubSpot."] : [])
    ].join("\n");
    events.push({
      sourceType: "hubspot_due_bundle",
      sourceKey,
      sourceMembers: members.map((task) => task.id),
      resource: {
        summary: title,
        description,
        start: { dateTime: start, timeZone: TIME_ZONE },
        end: { dateTime: end, timeZone: TIME_ZONE },
        visibility: "private",
        transparency: "transparent",
        reminders: { useDefault: true }
      }
    });
  }

  if (overdue.length) {
    overdue.sort((a, b) => priorityOrder(a) - priorityOrder(b) ||
      (a.due ?? 0) - (b.due ?? 0) || a.title.localeCompare(b.title));
    const today = localDateKey(nowMillis);
    const hourParts = new Intl.DateTimeFormat("en-GB", { timeZone: TIME_ZONE, hour: "2-digit", hourCycle: "h23" }).formatToParts(new Date(nowMillis));
    const localHour = Number(hourParts.find((part) => part.type === "hour")?.value || "0");
    const dateKey = localHour < 9 ? today : nextDateKey(today);
    const range = makeLocalTimedRange(dateKey, 9, 0, 20);
    events.push({
      sourceType: "hubspot_overdue_review",
      sourceKey: dateKey,
      sourceMembers: overdue.map((task) => task.id),
      resource: {
        summary: "HubSpot overdue review — " + overdue.length + " active tasks",
        description: [
          "Daily triage reminder for open, past-due HubSpot tasks.",
          "DEFERRED tasks are deliberately excluded from this roll-up.",
          "HubSpot remains the source of truth; this event contains titles and task links only.",
          "",
          ...overdue.slice(0, 40).map((task) => renderTaskLine(task, portalId)),
          ...(overdue.length > 40 ? ["\n+" + (overdue.length - 40) + " more overdue task(s)."] : [])
        ].join("\n"),
        ...range,
        visibility: "private",
        transparency: "transparent",
        reminders: { useDefault: true }
      }
    });
  }

  return {
    tasks,
    events,
    activeTaskIds: new Set(tasks.map((task) => task.id)),
    futureTaskCount: tasks.filter((task) => task.due != null && task.due > nowMillis).length,
    overdueTaskCount: overdue.length,
    deferredPastDueCount: tasks.filter((task) => task.status === "DEFERRED" &&
      task.due != null && task.due <= nowMillis).length,
    untimedTaskCount: untimed
  };
}

export function buildEstateRoadmapPlan(roadmap, nowMillis, maxAgeHours = 36) {
  if (!roadmap || !roadmap.generated || !Array.isArray(roadmap.upcoming)) {
    return { fresh: false, reason: "invalid_or_missing_feed", events: [] };
  }
  const generatedAt = Date.parse(roadmap.generated);
  if (!Number.isFinite(generatedAt)) {
    return { fresh: false, reason: "invalid_generated_timestamp", events: [] };
  }
  const ageHours = (nowMillis - generatedAt) / 3600000;
  if (ageHours < -1 || ageHours > maxAgeHours) {
    return { fresh: false, reason: "stale_feed", generated: roadmap.generated, ageHours, events: [] };
  }

  const today = localDateKey(nowMillis);
  const byDate = new Map();
  for (const item of roadmap.upcoming) {
    if (!item || typeof item.date !== "string" || item.date < today) continue;
    if (!item.institution || !item.what) continue;
    if (!byDate.has(item.date)) byDate.set(item.date, []);
    byDate.get(item.date).push(item);
  }

  const events = [];
  for (const [dateKey, items] of byDate.entries()) {
    items.sort((a, b) => String(a.institution).localeCompare(String(b.institution)) ||
      String(a.what).localeCompare(String(b.what)));
    const description = [
      "Automatically maintained from the public BucklerFamily.estate Dartboard roadmap.",
      "Snapshot generated: " + roadmap.generated,
      "A roadmap entry is a diarised matter, not a conclusion that a legal deadline has been met or missed.",
      "",
      ...items.slice(0, 60).map((item) => {
        const ref = item.ev ? " [" + item.ev + "]" : "";
        return "- " + item.institution + ": " + item.what + ref +
          (item.url ? "\n  " + item.url : "");
      }),
      ...(items.length > 60 ? ["\n+" + (items.length - 60) + " more matter(s)."] : [])
    ].join("\n");
    events.push({
      sourceType: "estate_roadmap_day",
      sourceKey: dateKey,
      sourceMembers: items.map((item) => String(item.lane || item.ev || item.what)),
      resource: {
        summary: "Estate matters — " + items.length + " diarised item(s)",
        description,
        start: { date: dateKey },
        end: { date: nextDateKey(dateKey) },
        visibility: "private",
        transparency: "transparent"
      }
    });
  }
  return {
    fresh: true,
    generated: roadmap.generated,
    ageHours,
    events
  };
}
