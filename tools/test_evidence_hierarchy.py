#!/usr/bin/env python3
"""Small synthetic integration test for theme-local catalogue slices."""
import json
import pathlib
import sqlite3
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import section_dbs

def seed_schema(con):
    ddl = [
        "CREATE TABLE meta(k TEXT PRIMARY KEY, v TEXT)",
        "CREATE TABLE themes(id TEXT PRIMARY KEY, title TEXT)",
        "CREATE TABLE artifacts(id INTEGER PRIMARY KEY, title TEXT, sha TEXT)",
        "CREATE TABLE locations(aid INTEGER, theme TEXT, path TEXT, url TEXT)",
        "CREATE TABLE evidence_catalogue(ev TEXT PRIMARY KEY, artifact_id INTEGER, path TEXT, evidence_grade INTEGER, independent_origin_id TEXT, aliases_json TEXT, grade_note TEXT, title TEXT)",
        "CREATE TABLE evidence_grades(ev TEXT, grade INTEGER, origin TEXT, path TEXT, note TEXT)",
        "CREATE TABLE evidence_catalogue_meta(key TEXT PRIMARY KEY, value TEXT)",
        "CREATE TABLE evidence_grade_scale(grade INTEGER PRIMARY KEY, meaning TEXT)",
        "CREATE TABLE evidence_text(aid INTEGER, path TEXT, title TEXT, body TEXT, body_chars INTEGER, truncated INTEGER)",
        "CREATE TABLE artifact_assessments(ev TEXT PRIMARY KEY, artifact_id INTEGER, description TEXT, description_status TEXT, transcript TEXT, transcript_status TEXT, interpretation TEXT, interpretation_status TEXT, source_verification_status TEXT, limitations TEXT, updated_at TEXT)",
        "CREATE TABLE observations(id TEXT PRIMARY KEY, slug TEXT, seq INTEGER, title TEXT, theme TEXT, observation_type TEXT, status TEXT, summary TEXT, analysis TEXT, limits TEXT, test_questions_json TEXT, related_page TEXT, page_path TEXT, updated_at TEXT)",
        "CREATE TABLE observation_refs(observation_id TEXT, seq INTEGER, ev TEXT, path TEXT, role TEXT, note TEXT, artifact_id INTEGER)",
        "CREATE TABLE section_records(theme TEXT, kind TEXT, id TEXT, seq INTEGER, data TEXT)",
        "CREATE TABLE layers(id TEXT PRIMARY KEY, title TEXT)",
        "CREATE TABLE layer_items(layer TEXT, id TEXT)",
        "CREATE TABLE layer_refs(layer TEXT, item TEXT, aid INTEGER, ev TEXT, path TEXT)",
        "CREATE TABLE layer_deps(layer TEXT, depends_on TEXT)",
        "CREATE TABLE edges(src TEXT, rel TEXT, dst TEXT)",
        "CREATE TABLE nodes(id TEXT PRIMARY KEY, kind TEXT, label TEXT)",
    ]
    for statement in ddl:
        con.execute(statement)
    con.execute("INSERT INTO meta VALUES('artifacts','2')")
    con.executemany("INSERT INTO themes VALUES(?,?)", [("wiki", "Wiki"), ("records", "Records"), ("nomenclature", "Nomenclature"), ("research", "Research"), ("chat", "Chat")])
    con.executemany("INSERT INTO artifacts VALUES(?,?,?)", [
        (1, "Wiki evidence register", "sha-wiki"),
        (2, "1955 possession order entry", "sha-1955"),
        (3, "Unrelated chat artifact", "sha-chat"),
        (4, "Name variants index", "sha-nomenclature"),
    ])
    con.executemany("INSERT INTO locations VALUES(?,?,?,?)", [
        (1, "wiki", "/wiki/evidence/", "/wiki/evidence/"),
        (2, "research", "/research/evidence/ev-0001-order/", "/research/evidence/ev-0001-order/"),
        (3, "chat", "/chat/unrelated.json", "/chat/unrelated.json"),
        (4, "nomenclature", "/nomenclature/c/cedwyn-estate/", "/nomenclature/c/cedwyn-estate/"),
    ])
    con.executemany("INSERT INTO evidence_catalogue VALUES(?,?,?,?,?,?,?,?)", [
        ("EV-0001", 2, "/research/evidence/ev-0001-order/", None, None, "[]", "not assessed", "1955 order entry"),
        ("EV-0002", None, "/research/evidence/ev-0002-pending/", None, None, "[]", "not yet linked to a built artifact", "Pending catalogue entry"),
    ])
    con.execute("INSERT INTO evidence_text VALUES(?,?,?,?,?,?)", (2, "/research/evidence/ev-0001-order/", "1955 order entry", "Order known by recital", 22, 0))
    con.executemany("INSERT INTO artifact_assessments VALUES(?,?,?,?,?,?,?,?,?,?,?)", [
        ("EV-0001", 2, "", "not_assessed", "", "not_assessed", "", "not_assessed", "not_assessed", "", "2026-10-29"),
        ("EV-0002", None, "", "not_assessed", "", "not_assessed", "", "not_assessed", "not_assessed", "", "2026-10-29"),
    ])
    con.execute("INSERT INTO observations VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
        "OBS-0001", "twelve-year-period-recurrence", 1, "Twelve-year recurrence", "wiki",
        "chronological_pattern", "working_observation", "Pattern summary", "Analysis", "Limits",
        '["Check dates"]', None, "/wiki/observations/twelve-year-period-recurrence/", "2026-10-29"))
    con.execute("INSERT INTO observation_refs VALUES(?,?,?,?,?,?,?)", (
        "OBS-0001", 1, "EV-0001", "/research/evidence/ev-0001-order/", "judgment recital", "Check original", 2))
    con.commit()

def main():
    with tempfile.TemporaryDirectory() as td:
        dist = pathlib.Path(td)
        con = sqlite3.connect(":memory:")
        seed_schema(con)
        results = section_dbs.run(con, dist, {"themes": [{"id": "wiki"}]}, 4096)
        config_path = dist / "wiki" / "_db" / "config.json"
        assert config_path.exists(), "section config was not written"
        config = json.loads(config_path.read_text())
        assert config["urlPrefix"] == "/wiki/_db/section.sqlite."
        files = sorted((dist / "wiki" / "_db").glob("section.sqlite.*"))
        assert files, "section database chunks were not written"
        raw = b"".join(p.read_bytes() for p in files)
        check = sqlite3.connect(":memory:")
        check.deserialize(raw)
        assert check.execute("SELECT title FROM observations WHERE id='OBS-0001'").fetchone()[0] == "Twelve-year recurrence"
        assert check.execute("SELECT ev FROM observation_refs WHERE observation_id='OBS-0001'").fetchone()[0] == "EV-0001"
        assert check.execute("SELECT title FROM evidence_catalogue WHERE ev='EV-0001'").fetchone()[0] == "1955 order entry"
        assert check.execute("SELECT count(*) FROM evidence_catalogue").fetchone()[0] == 2, "Wiki slice must expose every Level 1 catalogue row, including pending records without linked artifact bytes"
        assert check.execute("SELECT description_status FROM artifact_assessments WHERE ev='EV-0002'").fetchone()[0] == "not_assessed"
        coverage = check.execute(
            "SELECT COUNT(*) AS total, "
            "SUM(CASE WHEN trim(COALESCE(aa.description,''))<>'' THEN 1 ELSE 0 END) AS described, "
            "SUM(CASE WHEN trim(COALESCE(aa.transcript,''))<>'' THEN 1 ELSE 0 END) AS transcribed, "
            "SUM(CASE WHEN trim(COALESCE(aa.interpretation,''))<>'' THEN 1 ELSE 0 END) AS interpreted "
            "FROM evidence_catalogue ec LEFT JOIN artifact_assessments aa ON aa.ev=ec.ev"
        ).fetchone()
        assert coverage == (2, 0, 0, 0), "coverage counts should include pending records and only count populated fields"
        assert check.execute("SELECT count(*) FROM artifacts").fetchone()[0] == 3, "wiki-area slice should retain local and referenced artifacts but omit the unrelated artifact"
        check.close()
        arcade_config = dist / "arcade" / "_db" / "config.json"
        assert arcade_config.exists(), "the merged Arcade page area needs its own database"
        assert json.loads(arcade_config.read_text())["urlPrefix"] == "/arcade/_db/section.sqlite."
        con.close()

    area_doc = json.loads((ROOT / "data" / "site-areas.json").read_text())
    areas = area_doc["areas"]
    assert len(areas) == 37
    assert len({a["serendipity_slot"] for a in areas}) == 37
    hubspot_area = next(a for a in areas if a["id"] == "hubspot")
    assert hubspot_area["serendipity_slot"] == 37 and hubspot_area["path"] == "/hubspot/"
    assert hubspot_area["tithe_parcel_number"] is None, "digital site-area slot 37 is not a historic tithe plot"
    themes = [t for a in areas for t in a["source_themes"]]
    assert len(themes) == 45 and len(set(themes)) == 45
    assert all(a["tithe_parcel_number"] is None for a in areas), "must not invent historical plot numbers"
    # Exercise the same 37-area data contract used by the homepage generator.
    sys.path.insert(0, str(ROOT / "tools"))
    import home
    theme_cfg = json.loads((ROOT / "themes.json").read_text())
    by_id = {t["id"]: t for t in theme_cfg["themes"]}
    home_cfg = dict(theme_cfg)
    home_cfg["themes"] = []
    for area in areas:
        sources = area.get("source_themes", [])
        primary = by_id.get(sources[0], {}) if sources else {}
        home_cfg["themes"].append({
            "id": area["id"], "title": area["title"],
            "group": primary.get("group") or theme_cfg.get("default_group") or "",
            "cy": primary.get("cy") or "", "es": primary.get("es") or ""
        })
    home_html = home.render(home_cfg)
    assert home_html.count('class="entry"') == 37, "homepage should display exactly 37 public areas"

    obs_doc = json.loads((ROOT / "data" / "observations.json").read_text())
    assert len(obs_doc["items"]) >= 3
    assert all(o.get("refs") for o in obs_doc["items"]), "every seeded observation must cite artifact records"
    print("Evidence hierarchy tests passed: section DB, linked observation, 37 areas / 45 source themes, no invented parcel IDs.")

if __name__ == "__main__":
    main()
