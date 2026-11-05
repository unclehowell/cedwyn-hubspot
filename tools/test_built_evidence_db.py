#!/usr/bin/env python3
"""Integration checks against the exact chunked SQLite catalogue produced by build_db.py."""
import json
import pathlib
import sqlite3
import sys
import tempfile

DIST = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "dist")
DB_DIR = DIST / "db"
CONFIG = json.loads((DB_DIR / "config.json").read_text(encoding="utf-8"))
STATS = json.loads((DB_DIR / "stats.json").read_text(encoding="utf-8"))
chunks = sorted(
    DB_DIR.glob("cedwyn.sqlite3.*"),
    key=lambda p: int(p.name.rsplit(".", 1)[1])
)
if not chunks:
    raise SystemExit("FAIL: no chunked central SQLite database found")
if len(chunks) != int(STATS.get("chunks", -1)):
    raise SystemExit(f"FAIL: chunk count {len(chunks)} != stats count {STATS.get('chunks')}")

with tempfile.TemporaryDirectory(prefix="cedwyn-db-check-") as td:
    reconstructed = pathlib.Path(td) / "cedwyn.sqlite3"
    with reconstructed.open("wb") as out:
        for part in chunks:
            with part.open("rb") as src:
                while True:
                    block = src.read(4 * 1024 * 1024)
                    if not block:
                        break
                    out.write(block)
    if reconstructed.stat().st_size != int(CONFIG["databaseLengthBytes"]):
        raise SystemExit("FAIL: reconstructed database byte length disagrees with config.json")

    con = sqlite3.connect(f"file:{reconstructed}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA query_only=ON")
    integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity != "ok":
        raise SystemExit(f"FAIL: SQLite integrity_check: {integrity}")

    def count(table):
        return int(con.execute(f"SELECT count(*) FROM {table}").fetchone()[0])

    expected_min = {
        "evidence_catalogue": 81,
        "evidence_text": 1,
        "artifact_assessments": 81,
        "observations": 3,
        "observation_refs": 18,
    }
    counts = {table: count(table) for table in expected_min}
    for table, minimum in expected_min.items():
        if counts[table] < minimum:
            raise SystemExit(f"FAIL: {table} has {counts[table]} rows; expected at least {minimum}")

    # Execute the same evidence and observation joins used by agent-tools.js.
    row = con.execute(
        """SELECT ec.ev, ec.artifact_id, ec.path, ec.evidence_grade, ec.independent_origin_id,
                  ec.aliases_json, ec.grade_note, ec.title,
                  et.body AS record_text, et.body_chars, et.truncated,
                  a.sha, a.kind, a.mime, a.bytes, a.year_min, a.year_max,
                  aa.description, aa.description_status, aa.transcript, aa.transcript_status,
                  aa.interpretation, aa.interpretation_status, aa.source_verification_status, aa.limitations
             FROM evidence_catalogue ec
             LEFT JOIN evidence_text et ON et.aid=ec.artifact_id
             LEFT JOIN artifacts a ON a.id=ec.artifact_id
             LEFT JOIN artifact_assessments aa ON aa.ev=ec.ev
            WHERE lower(ec.ev)=lower(?) LIMIT 1""",
        ("EV-0617",)
    ).fetchone()
    if not row or row["artifact_id"] is None or not row["record_text"]:
        raise SystemExit("FAIL: EV-0617 does not resolve to its built artifact text and assessment")
    if not row["description_status"] or not row["interpretation_status"]:
        raise SystemExit("FAIL: assessment states are missing on the real evidence row")

    # The site-level loader must be present on a nested evidence page, not only the theme home.
    evidence_page = DIST / "research" / "evidence" / "ev-0617-twelve-year-limitation-rule-1879-1940" / "index.html"
    if not evidence_page.is_file():
        raise SystemExit(f"FAIL: expected nested Level 1 evidence page is missing: {evidence_page}")
    page_html = evidence_page.read_text(encoding="utf-8", errors="replace")
    if 'src="/_cedwyn/agent-tools.js' not in page_html and "src='/_cedwyn/agent-tools.js" not in page_html:
        raise SystemExit("FAIL: central agent tools script not injected on the nested evidence page")

    # The production full-text search join must resolve the indexed evidence catalogue.
    search = con.execute(
        """SELECT DISTINCT ec.ev, ec.title, ec.path, snippet(fts, 1, '[', ']', ' … ', 18) AS excerpt
             FROM fts
             JOIN evidence_catalogue ec ON ec.artifact_id=CAST(fts.aid AS INTEGER)
            WHERE fts MATCH ? AND ec.ev=? LIMIT 1""",
        ("twelve", "EV-0617")
    ).fetchall()
    if not search or search[0]["ev"] != "EV-0617":
        raise SystemExit("FAIL: full-text search does not resolve EV-0617 through the indexed evidence join")

    grade = con.execute(
        "SELECT meaning FROM evidence_grade_scale WHERE grade=?",
        (row["evidence_grade"],)
    ).fetchone() if row["evidence_grade"] is not None else None
    if row["evidence_grade"] is not None and not grade:
        raise SystemExit("FAIL: evidence grade has no published grade-scale meaning")

    # Check the related-location, graph, layer and Level 2 observation query shapes.
    con.execute("SELECT theme, path, url FROM locations WHERE aid=? AND theme<>'_blob' LIMIT 40",
                (row["artifact_id"],)).fetchall()
    con.execute("""SELECT e.rel, e.dst, a.title, a.kind, a.id AS artifactId
                     FROM edges e LEFT JOIN artifacts a ON e.dst=('a:' || a.id)
                    WHERE e.src=? ORDER BY e.rel, e.dst LIMIT 50""",
                ("a:" + str(row["artifact_id"]),)).fetchall()
    con.execute("""SELECT lr.layer AS layerId, l.title AS layerTitle, lr.item AS itemId,
                          li.kind AS itemKind, li.date AS date, li.event AS event,
                          li.blow AS interpretationNote, li.label AS label,
                          lr.ev AS referencedEvidence, lr.path AS referencedPath
                     FROM layer_refs lr
                     LEFT JOIN layers l ON l.id=lr.layer
                     LEFT JOIN layer_items li ON li.layer=lr.layer AND li.id=lr.item
                    WHERE lower(lr.ev)=lower(?) OR lr.aid=?
                    ORDER BY l.title, li.seq LIMIT 40""",
                (row["ev"], row["artifact_id"])).fetchall()
    obs = con.execute(
        "SELECT * FROM observations WHERE lower(id)=lower(?) OR lower(slug)=lower(?) LIMIT 2",
        ("OBS-0001", "OBS-0001")
    ).fetchone()
    if not obs or "twelve-year" not in obs["slug"]:
        raise SystemExit("FAIL: Level 2 twelve-year observation is missing")
    refs = con.execute(
        """SELECT r.ev, r.path, r.role, r.note, r.artifact_id AS artifactId,
                  ec.title, ec.independent_origin_id AS independentOriginId,
                  ec.evidence_grade AS evidenceGrade, ec.grade_note AS gradeNote
             FROM observation_refs r LEFT JOIN evidence_catalogue ec ON ec.ev=r.ev
            WHERE r.observation_id=? ORDER BY r.seq""",
        (obs["id"],)
    ).fetchall()
    if len(refs) < 6 or not any(r["ev"] == "EV-0617" for r in refs):
        raise SystemExit("FAIL: Level 2 observation references are not joined to Level 1 evidence")

    meta = con.execute("SELECT key, value FROM evidence_catalogue_meta").fetchall()
    con.close()

    print(json.dumps({
        "status": "passed",
        "database_bytes": reconstructed.stat().st_size,
        "chunk_count": len(chunks),
        "sqlite_integrity": integrity,
        "counts": counts,
        "fts_matches_for_twelve": len(search),
        "level_1_record": "EV-0617",
        "level_2_observation": "OBS-0001",
        "observation_reference_count": len(refs),
        "catalogue_metadata_rows": len(meta)
    }, ensure_ascii=False))
