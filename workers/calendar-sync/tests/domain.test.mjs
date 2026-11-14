import test from "node:test";
import assert from "node:assert/strict";
import {
  buildHubSpotPlan,
  buildEstateRoadmapPlan,
  localDateKey,
  nextDateKey,
  parseHubSpotTimestamp,
  makeLocalTimedRange
} from "../domain.js";

const NOW = Date.parse("2026-11-14T11:00:00Z");

function task(id, subject, due, status = "NOT_STARTED", priority = "MEDIUM", open = true) {
  return {
    id,
    properties: {
      hs_task_subject: subject,
      hs_timestamp: due,
      hs_task_status: status,
      hs_task_priority: priority,
      hs_task_type: "TODO",
      hs_task_is_open: String(open),
      hs_task_body: "MUST NOT BE COPIED TO CALENDAR"
    }
  };
}

test("parses HubSpot millisecond and ISO timestamps", () => {
  assert.equal(parseHubSpotTimestamp("1794650400000"), 1794650400000);
  assert.equal(parseHubSpotTimestamp("2026-11-14T11:00:00Z"), NOW);
  assert.equal(parseHubSpotTimestamp(null), null);
});

test("Amsterdam local date respects the requested timezone", () => {
  assert.equal(localDateKey("2026-11-13T23:30:00Z"), "2026-11-14");
  assert.equal(nextDateKey("2026-11-30"), "2026-12-01");
  const range = makeLocalTimedRange("2026-11-14", 9, 0, 20);
  assert.equal(range.start.dateTime, "2026-11-14T09:00:00");
  assert.equal(range.start.timeZone, "Europe/Amsterdam");
  assert.equal(range.end.dateTime, "2026-11-14T09:20:00");
});

test("groups future tasks at the same exact due time", () => {
  const due = "2026-11-16T09:00:00Z";
  const plan = buildHubSpotPlan([
    task("1", "Welsh Government reply", due, "NOT_STARTED", "HIGH"),
    task("2", "Glamorgan Archives reply", due, "WAITING", "MEDIUM"),
    task("3", "Deferred future work", due, "DEFERRED", "LOW"),
    task("4", "Completed work", due, "COMPLETED", "HIGH", false)
  ], NOW, 149419802);

  assert.equal(plan.futureTaskCount, 3);
  assert.equal(plan.events.length, 1);
  assert.equal(plan.events[0].sourceType, "hubspot_due_bundle");
  assert.equal(plan.events[0].sourceMembers.length, 3);
  assert.match(plan.events[0].resource.summary, /3 tasks due/);
  assert.ok(!plan.events[0].resource.description.includes("MUST NOT BE COPIED"));
});

test("overdue roll-up excludes deliberately deferred tasks", () => {
  const overdue = "2026-11-10T09:00:00Z";
  const plan = buildHubSpotPlan([
    task("1", "Active overdue request", overdue, "NOT_STARTED", "HIGH"),
    task("2", "Waiting overdue response", overdue, "WAITING", "MEDIUM"),
    task("3", "Deferred research", overdue, "DEFERRED", "HIGH"),
    task("4", "Future reply", "2026-11-17T09:00:00Z", "NOT_STARTED", "LOW")
  ], NOW, 149419802);

  const rollup = plan.events.find((item) => item.sourceType === "hubspot_overdue_review");
  assert.equal(plan.overdueTaskCount, 2);
  assert.ok(rollup);
  assert.match(rollup.resource.summary, /2 active tasks/);
  assert.ok(!rollup.resource.description.includes("Deferred research"));
  assert.equal(plan.deferredPastDueCount, 1);
});

test("stale public roadmap snapshot is rejected", () => {
  const roadmap = {
    generated: "2026-11-09T18:34:21Z",
    upcoming: [{ date: "2026-11-16", institution: "Glamorgan Archives", what: "Reply expected" }]
  };
  const result = buildEstateRoadmapPlan(roadmap, NOW, 36);
  assert.equal(result.fresh, false);
  assert.equal(result.reason, "stale_feed");
  assert.equal(result.events.length, 0);
});

test("fresh roadmap matters are grouped by date and use all-day events", () => {
  const roadmap = {
    generated: "2026-11-14T10:30:00Z",
    upcoming: [
      { date: "2026-11-16", lane: "archives", institution: "Glamorgan Archives", what: "Reply expected", ev: "EV-001", url: "https://example.test/ev-001" },
      { date: "2026-11-16", lane: "vale", institution: "Vale Council", what: "FOI reply expected", ev: "EV-002" },
      { date: "2026-11-13", institution: "Historic item", what: "Past matter" }
    ]
  };
  const result = buildEstateRoadmapPlan(roadmap, NOW, 36);
  assert.equal(result.fresh, true);
  assert.equal(result.events.length, 1);
  assert.equal(result.events[0].sourceKey, "2026-11-16");
  assert.equal(result.events[0].resource.start.date, "2026-11-16");
  assert.equal(result.events[0].resource.end.date, "2026-11-17");
  assert.match(result.events[0].resource.summary, /2 diarised items/);
});
