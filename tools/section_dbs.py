#!/usr/bin/env python3
"""Build compact, read-only SQLite views of theme and public-area records.

The central catalogue is authoritative. Source-theme slices are retained for legacy
routes; multi-theme visitor areas get an aggregate slice at their public route.
"""
import json
import os
import pathlib
import sqlite3

ROOT = pathlib.Path(__file__).resolve().parent.parent
TABLES = (
    "meta", "themes", "artifacts", "locations", "evidence_catalogue",
    "evidence_grades", "evidence_catalogue_meta", "evidence_grade_scale",
    "evidence_text", "artifact_assessments", "observations", "observation_refs",
    "section_records", "estate_parcels", "parcel_events", "estate_parcel_model", "estate_parcel_model_events", "layers", "layer_items", "layer_refs", "layer_deps",
    "captures", "nodes", "edges",
)

def copy_table(src, dst, table, where="1=1", params=()):
    schema = src.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    if not schema or not schema[0] or table == "fts":
        return 0
    dst.execute(schema[0])
    columns = [r[1] for r in src.execute('PRAGMA table_info("' + table + '")')]
    rows = src.execute('SELECT * FROM "' + table + '" WHERE ' + where, params).fetchall()
    if rows:
        marks = ",".join("?" for _ in columns)
        dst.executemany('INSERT INTO "' + table + '" VALUES (' + marks + ')', rows)
    return len(rows)

def in_clause(values):
    return "IN (" + ",".join("?" for _ in values) + ")"

def build_slice(con, dist, area_id, source_ids, chunk_size):
    source_ids = list(dict.fromkeys(source_ids))
    if not source_ids:
        return {"bytes": 0, "chunks": 0, "artifacts": 0, "observations": 0}
    ph = ",".join("?" for _ in source_ids)
    themes_filter = "theme " + in_clause(source_ids)
    obs_filter = "o.theme " + in_clause(source_ids)
    outdir = pathlib.Path(dist) / area_id / "_db"
    outdir.mkdir(parents=True, exist_ok=True)
    for pattern in ("section.sqlite", "section.sqlite.*", "config.json"):
        for old in outdir.glob(pattern):
            if old.is_file():
                old.unlink()
    tmp = outdir / "section.sqlite"
    dst = sqlite3.connect(tmp)
    dst.execute("PRAGMA journal_mode=OFF")
    dst.execute("PRAGMA synchronous=OFF")

    # Page-local artifacts plus source artifacts referenced by observations in this area.
    artifact_where = (
        "EXISTS (SELECT 1 FROM locations l WHERE l.aid=artifacts.id AND l.theme " + in_clause(source_ids) + ") "
        "OR artifacts.id IN (SELECT r.artifact_id FROM observation_refs r "
        "JOIN observations o ON o.id=r.observation_id WHERE " + obs_filter + " AND r.artifact_id IS NOT NULL)"
    )
    params = tuple(source_ids) + tuple(source_ids)
    if area_id == "wiki":
        # The Wiki's evidence register is the public browser for the whole Level 1 catalogue.
        artifact_where = "(" + artifact_where + ") OR artifacts.id IN (SELECT artifact_id FROM evidence_catalogue WHERE artifact_id IS NOT NULL)"
    copy_table(con, dst, "meta", "k IN ('db_version','artifacts','locations','evidence_records','observations')")
    copy_table(con, dst, "themes", "id " + in_clause(source_ids), source_ids)
    copy_table(con, dst, "observations", themes_filter, source_ids)
    copy_table(con, dst, "artifacts", artifact_where, params)
    _location_where = (
        "aid IN (SELECT aid FROM locations WHERE " + themes_filter + ") OR aid IN "
        "(SELECT rr.artifact_id FROM observation_refs rr JOIN observations oo ON oo.id=rr.observation_id "
        "WHERE oo.theme " + in_clause(source_ids) + " AND rr.artifact_id IS NOT NULL)"
    )
    _location_params = tuple(source_ids) * 2
    if area_id == "wiki":
        _location_where += " OR aid IN (SELECT artifact_id FROM evidence_catalogue WHERE artifact_id IS NOT NULL)"
    copy_table(con, dst, "locations", _location_where, _location_params)
    _catalogue_where = (
        "artifact_id IN (SELECT aid FROM locations WHERE " + themes_filter + ") "
        "OR artifact_id IN (SELECT rr.artifact_id FROM observation_refs rr JOIN observations oo ON oo.id=rr.observation_id "
        "WHERE oo.theme " + in_clause(source_ids) + " AND rr.artifact_id IS NOT NULL) "
        "OR ev IN (SELECT rr.ev FROM observation_refs rr JOIN observations oo ON oo.id=rr.observation_id "
        "WHERE oo.theme " + in_clause(source_ids) + " AND rr.ev IS NOT NULL)"
    )
    _catalogue_params = tuple(source_ids) * 3
    if area_id == "wiki":
        _catalogue_where, _catalogue_params = "1=1", ()
    copy_table(con, dst, "evidence_catalogue", _catalogue_where, _catalogue_params)
    _grade_where = (
        "ev IN (SELECT ev FROM evidence_catalogue WHERE artifact_id IN "
        "(SELECT aid FROM locations WHERE " + themes_filter + ") OR ev IN "
        "(SELECT rr.ev FROM observation_refs rr JOIN observations oo ON oo.id=rr.observation_id "
        "WHERE oo.theme " + in_clause(source_ids) + " AND rr.ev IS NOT NULL))"
    )
    _grade_params = tuple(source_ids) * 2
    if area_id == "wiki":
        _grade_where, _grade_params = "ev IN (SELECT ev FROM evidence_catalogue)", ()
    copy_table(con, dst, "evidence_grades", _grade_where, _grade_params)
    copy_table(con, dst, "evidence_catalogue_meta")
    copy_table(con, dst, "evidence_grade_scale")
    _text_where = (
        "aid IN (SELECT aid FROM locations WHERE " + themes_filter + ") OR aid IN "
        "(SELECT rr.artifact_id FROM observation_refs rr JOIN observations oo ON oo.id=rr.observation_id "
        "WHERE oo.theme " + in_clause(source_ids) + " AND rr.artifact_id IS NOT NULL)"
    )
    _text_params = tuple(source_ids) * 2
    if area_id == "wiki":
        _text_where, _text_params = "aid IN (SELECT artifact_id FROM evidence_catalogue WHERE artifact_id IS NOT NULL)", ()
    copy_table(con, dst, "evidence_text", _text_where, _text_params)
    _assessment_where = (
        "ev IN (SELECT ev FROM evidence_catalogue WHERE artifact_id IN "
        "(SELECT aid FROM locations WHERE " + themes_filter + ") OR ev IN "
        "(SELECT rr.ev FROM observation_refs rr JOIN observations oo ON oo.id=rr.observation_id "
        "WHERE oo.theme " + in_clause(source_ids) + " AND rr.ev IS NOT NULL))"
    )
    _assessment_params = tuple(source_ids) * 2
    if area_id == "wiki":
        _assessment_where, _assessment_params = "ev IN (SELECT ev FROM evidence_catalogue)", ()
    copy_table(con, dst, "artifact_assessments", _assessment_where, _assessment_params)
    copy_table(con, dst, "observation_refs",
        "observation_id IN (SELECT id FROM observations WHERE " + themes_filter + ")", source_ids)
    copy_table(con, dst, "section_records", themes_filter, source_ids)
    # Parent register -> area child DB: only this webapp's provisional slot, with its events.
    copy_table(con, dst, "estate_parcels", "area_id=?", (area_id,))
    copy_table(con, dst, "parcel_events", "parcel_id IN (SELECT parcel_id FROM estate_parcels WHERE area_id=?)", (area_id,))
    # The compact shared A1 / A2 / B / C working model is included for context in each child DB.
    copy_table(con, dst, "estate_parcel_model")
    copy_table(con, dst, "estate_parcel_model_events")

    # Keep the chronology layer(s) that cite relevant artifacts, plus the 1000 Cuts layer.
    layer_refs_where = (
        "lr.aid IN (SELECT aid FROM locations WHERE " + themes_filter + ") OR lr.aid IN "
        "(SELECT rr.artifact_id FROM observation_refs rr JOIN observations oo ON oo.id=rr.observation_id "
        "WHERE oo.theme " + in_clause(source_ids) + " AND rr.artifact_id IS NOT NULL)"
    )
    layer_params = tuple(source_ids) * 2 + (area_id,)
    copy_table(con, dst, "layers",
        "id IN (SELECT DISTINCT lr.layer FROM layer_refs lr WHERE " + layer_refs_where + ") OR ?='thousand-cuts'",
        layer_params)
    copy_table(con, dst, "layer_items",
        "layer IN (SELECT DISTINCT lr.layer FROM layer_refs lr WHERE " + layer_refs_where + ") OR ?='thousand-cuts'",
        layer_params)
    copy_table(con, dst, "layer_refs",
        "layer IN (SELECT DISTINCT lr.layer FROM layer_refs lr WHERE " + layer_refs_where + ") OR ?='thousand-cuts'",
        layer_params)
    copy_table(con, dst, "layer_deps",
        "layer IN (SELECT DISTINCT lr.layer FROM layer_refs lr WHERE " + layer_refs_where + ") OR ?='thousand-cuts'",
        layer_params)
    if area_id == "wayback":
        copy_table(con, dst, "captures")

    # Graph edges are limited to this slice's artifacts and observation nodes.
    edge_aids = (
        "SELECT aid FROM locations WHERE " + themes_filter +
        " UNION SELECT rr.artifact_id FROM observation_refs rr JOIN observations oo ON oo.id=rr.observation_id "
        "WHERE oo.theme " + in_clause(source_ids) + " AND rr.artifact_id IS NOT NULL"
    )
    edge_obs = "SELECT id FROM observations WHERE " + themes_filter
    edge_filter = (
        "src IN (SELECT 'a:'||aid FROM (" + edge_aids + ")) OR dst IN (SELECT 'a:'||aid FROM (" + edge_aids + ")) "
        "OR src IN (SELECT 'observation:'||id FROM (" + edge_obs + ")) "
        "OR dst IN (SELECT 'observation:'||id FROM (" + edge_obs + "))"
    )
    edge_params = tuple(source_ids) * 6
    copy_table(con, dst, "edges", edge_filter, edge_params)
    copy_table(con, dst, "nodes",
        "id IN (SELECT src FROM edges WHERE " + edge_filter + ") OR id IN (SELECT dst FROM edges WHERE " + edge_filter + ")",
        edge_params * 2)

    dst.commit()
    dst.execute("VACUUM")
    dst.close()
    raw = tmp.read_bytes()
    chunk_count = 0
    for offset in range(0, len(raw), chunk_size):
        (outdir / ("section.sqlite.%03d" % chunk_count)).write_bytes(raw[offset:offset + chunk_size])
        chunk_count += 1
    tmp.unlink()
    config = {
        "serverMode": "chunked",
        "requestChunkSize": chunk_size,
        "databaseLengthBytes": len(raw),
        "serverChunkSize": chunk_size,
        "urlPrefix": "/" + area_id + "/_db/section.sqlite.",
        "suffixLength": 3,
    }
    (outdir / "config.json").write_text(json.dumps(config, separators=(",", ":")) + "\n", encoding="utf-8")
    stats = {
        "bytes": len(raw),
        "chunks": chunk_count,
        "artifacts": con.execute(
            "SELECT count(DISTINCT aid) FROM locations WHERE " + themes_filter, source_ids
        ).fetchone()[0],
        "observations": con.execute(
            "SELECT count(*) FROM observations WHERE " + themes_filter, source_ids
        ).fetchone()[0],
    }
    return stats

def run(con, dist, cfg, chunk_size=None, include_areas=True):
    dist = pathlib.Path(dist)
    chunk_size = chunk_size or int(os.environ.get("DB_CHUNK", 256 * 1024))
    targets = {
        theme["id"]: [theme["id"]]
        for theme in cfg.get("themes", [])
    }
    if include_areas:
        area_file = ROOT / "data" / "site-areas.json"
        if area_file.exists():
            area_doc = json.loads(area_file.read_text(encoding="utf-8"))
            for area in area_doc.get("areas", []):
                sources = area.get("source_themes", [])
                # Multi-theme public areas get a consolidated database at the public route.
                if len(sources) > 1:
                    targets[area["id"]] = sources
    results = {}
    for area_id, source_ids in targets.items():
        results[area_id] = build_slice(con, dist, area_id, source_ids, chunk_size)
    print("section databases:", json.dumps(results, sort_keys=True))
    return results

if __name__ == "__main__":
    raise SystemExit("Import run(con, dist, cfg) from the catalogue build.")
