#!/usr/bin/env python3
"""Regression test for source-referenced structured records lacking a section HTML page."""
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import evidence_observations

with tempfile.TemporaryDirectory(prefix="cedwyn-evidence-page-test-") as td:
    dist = pathlib.Path(td)
    doc = __import__("json").loads((ROOT / "data" / "observations.json").read_text(encoding="utf-8"))
    created = evidence_observations.generate_missing_assessment_pages(dist, doc.get("items", []))
    page = dist / "research" / "evidence" / "ev-0617-twelve-year-limitation-rule-1879-1940" / "index.html"
    assert page.is_file(), "referenced EV-0617 needs a generated Level 1 page"
    html = page.read_text(encoding="utf-8")
    assert "EV-0617" in html
    assert "generated research entry" in html
    assert "not the original statutory text" in html
    assert "No evidence grade" in html
    assert "The recurrence is a pattern" not in html  # don't substitute Level 2 summary for Level 1 interpretation
    assert any(item.get("ev") == "EV-0617" for item in created), "missing page should be reported as generated"
print("Evidence-page test passed: EV-0617 gets a clearly labelled, ungraded Level 1 research page.")
