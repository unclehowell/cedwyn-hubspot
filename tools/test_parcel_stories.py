#!/usr/bin/env python3
"""Static checks for the 36 historic parcel-story slots alongside all Cedwyn site areas."""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
areas_doc = json.loads((ROOT / "data" / "site-areas.json").read_text(encoding="utf-8"))
stories_doc = json.loads((ROOT / "data" / "parcel-stories.json").read_text(encoding="utf-8"))
areas = areas_doc.get("areas", [])
stories = stories_doc.get("parcels", [])
assert stories_doc.get("schema") == "cedwyn_parcel_stories/v1"
assert len(areas) == 37 and len(stories) == 36
assert sum(1 for a in areas if a["id"] == "hubspot") == 1
assert {a["id"] for a in areas if a["id"] != "hubspot"} == {p["area_id"] for p in stories}
assert sorted(p["slot"] for p in stories) == list(range(1, 37))
assert len({p["parcel_id"] for p in stories}) == 36
assert all(p["historic_plot_number"] is None for p in stories)
assert all(p["mapping_status"] == "historic_plot_number_pending_verification" for p in stories)
assert all(len(p.get("events", [])) >= 1 for p in stories)
assert {m["model_id"] for m in stories_doc["parcel_model"]} == {"A", "A1", "A2", "B", "C"}
model = {m["model_id"]: m for m in stories_doc["parcel_model"]}
assert model["A1"]["parent_id"] == "A" and model["A2"]["parent_id"] == "A"
assert model["C"]["parent_id"] is None
assert "outside Parcel A" in model["A"]["description"]
assert all(e["source_ev"] == "EV-0215" for p in stories for e in p["events"])
assert {e["model_id"] for e in stories_doc["model_events"]} >= {"A1", "A2", "B", "C"}
assert any(e["title"].startswith("Alfred Thomas dies") and "EV-0284" in e.get("source_evs", []) for e in stories_doc["model_events"])
assert any(e["model_id"] == "A2" and "death date unknown" in e["date_text"].lower() for e in stories_doc["model_events"])
assert any(e["model_id"] == "B" and "12 years after May 1939" in e["date_text"] for e in stories_doc["model_events"])
panel = (ROOT / "web" / "_cedwyn" / "parcel-panel.js").read_text(encoding="utf-8")
assert "parcel && parcel.model_parcel_id && e.model_id === parcel.model_parcel_id" in panel
assert "makeSharedModelEventTable(modelEvents)" in panel
assert "not this webapp’s own chain of title" in panel
print("parcel story source OK: 37 public areas, 36 historic parcel slots, 5 working model records")
