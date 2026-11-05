#!/usr/bin/env node
'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

async function main() {
  const source = fs.readFileSync(path.join(__dirname, '..', 'web', '_cedwyn', 'agent-tools.js'), 'utf8');
  const queryCalls = [];
  let clientLoads = 0;
  let dbOpens = 0;

  const evidence = {
    ev: 'EV-0001', title: '1955 possession order entry',
    path: '/research/evidence/ev-0001-order/', evidence_grade: 2,
    independent_origin_id: 'origin-1955-order', aliases_json: '["GHF-E001"]',
    grade_note: 'The order is currently known through a later judgment.',
    excerpt: 'Published catalogue entry text.', record_text: 'Full published catalogue entry text.',
    body_chars: 72, truncated: 0, artifact_id: 5, sha: 'sha-1955',
    kind: 'page', mime: 'text/html', bytes: 1234, year_min: 1955, year_max: 1987,
    description: 'Neutral record description.', description_status: 'assessed',
    transcript: '', transcript_status: 'not_assessed',
    interpretation: 'Interpretation kept separate.', interpretation_status: 'assessed',
    source_verification_status: 'reviewed',
    limitations: 'Underlying order copy not independently inspected.'
  };
  const observation = {
    id: 'OBS-0001', slug: 'twelve-year-period-recurrence', seq: 1,
    title: 'The twelve-year period recurs', theme: 'wiki',
    observation_type: 'chronological_pattern', status: 'working_observation',
    summary: 'A pattern to test.', analysis: 'Compare each dated interval.',
    limits: 'Recurrence is not proof of a legal consequence.',
    test_questions_json: '["Check the dates and parcel"]',
    related_page: '/wiki/twelve-year-period/',
    page_path: '/wiki/observations/twelve-year-period-recurrence/',
    updated_at: '2026-10-29', reference_count: 1
  };
  const ref = {
    ev: 'EV-0001', path: evidence.path, role: 'judgment recital',
    note: 'Check the original order.', artifact_id: 5, title: evidence.title,
    independentOriginId: evidence.independent_origin_id,
    evidenceGrade: evidence.evidence_grade, gradeNote: evidence.grade_note
  };

  const db = {
    query: async (sql, params) => {
      queryCalls.push({ sql, params });
      if (sql.includes('FROM evidence_catalogue ec') && sql.includes('et.body AS excerpt')) return [evidence];
      if (sql.includes('FROM evidence_catalogue ec') && sql.includes('et.body AS record_text')) return [evidence];
      if (sql.includes('SELECT key, value FROM evidence_catalogue_meta')) return [{ key: 'version', value: 'test' }];
      if (sql.includes('SELECT meaning FROM evidence_grade_scale')) return [{ meaning: 'Judgment recital; underlying instrument not independently inspected.' }];
      if (sql.includes('FROM layer_refs lr')) return [];
      if (sql.includes('FROM locations')) return [{ theme: 'research', path: evidence.path, url: evidence.path }];
      if (sql.includes('FROM edges e')) return [{ rel: 'links', dst: 'a:6', title: 'Related page', kind: 'page', artifactId: 6 }];
      if (sql.includes('SELECT * FROM observations WHERE lower(id)')) return [observation];
      if (sql.includes('FROM observations o')) return [observation];
      if (sql.includes('FROM observation_refs r LEFT JOIN evidence_catalogue')) return [ref];
      return [];
    }
  };

  const window = {};
  const elements = new Map();
  function element(tag) {
    const attrs = {};
    return {
      tagName: tag.toUpperCase(), attrs, children: [],
      setAttribute(k, v) { attrs[k] = String(v); },
      getAttribute(k) { return attrs[k] || null; },
      appendChild(child) { this.children.push(child); if (child.id) elements.set(child.id, child); return child; },
      remove() {}, textContent: '', id: '', hidden: false
    };
  }
  const document = {
    readyState: 'complete', title: 'Cedwyn test page',
    body: element('body'), documentElement: element('html'),
    head: {
      appendChild(script) {
        if (script.src !== '/_cedwyn/cat.js') throw new Error('Unexpected script URL: ' + script.src);
        clientLoads++;
        window.Cedwyn = {
          db: () => { dbOpens++; return Promise.resolve(db); },
          graphql: () => Promise.resolve({ data: { search: [{
            theme: 'research', path: evidence.path, snippet: '1955 possession order',
            artifact: { id: 5, title: evidence.title, kind: 'page' }
          }] } })
        };
        if (typeof script.onload === 'function') script.onload();
        return script;
      }
    },
    createElement: element,
    getElementById(id) { return elements.get(id) || null; }
  };
  window.document = document;
  const context = {
    window, document, navigator: {},
    location: { href: 'https://cedwyn.bucklerfamily.estate/research/evidence/ev-0001-order/',
      origin: 'https://cedwyn.bucklerfamily.estate', pathname: '/research/evidence/ev-0001-order/' },
    console, URL, setTimeout, clearTimeout
  };
  vm.runInNewContext(source, context, { filename: 'agent-tools.js' });
  await new Promise(resolve => setTimeout(resolve, 0));

  const api = window.__cedwynWebMCP;
  assert.ok(api && typeof api.run === 'function', 'agent fallback API should be available');
  assert.equal(clientLoads, 0, 'catalogue client should load lazily, not on every page view');
  for (const name of ['search_central_evidence_catalogue', 'get_central_evidence_record',
    'search_central_observations', 'get_central_observation']) {
    assert.ok(api.tools.includes(name), 'missing tool: ' + name);
  }

  const publicSearch = await api.run('search_case_public_content', { q: '1955 possession order', theme: 'research' });
  assert.equal(publicSearch[0].artifact.id, 5, 'public content search should load and query the catalogue client');
  assert.equal(clientLoads, 1, 'catalogue client should only load once');

  const evidenceSearch = await api.run('search_central_evidence_catalogue', { q: 'EV-0001', limit: 5 });
  assert.equal(evidenceSearch.results[0].ev, 'EV-0001', 'central evidence search should return the record');
  assert.equal(evidenceSearch.results[0].assessment.interpretation, 'Interpretation kept separate.');

  const record = await api.run('get_central_evidence_record', { key: 'EV-0001' });
  assert.equal(record.found, true, 'central evidence record lookup should succeed');
  assert.equal(record.record.sourcePageText, 'Full published catalogue entry text.');
  assert.equal(record.record.chronologyAndLayerReferences.length, 0);

  const foundObservation = await api.run('get_central_observation', { key: 'OBS-0001' });
  assert.equal(foundObservation.found, true, 'Level 2 observation lookup should succeed');
  assert.equal(foundObservation.observation.references[0].ev, 'EV-0001');

  const observationSearch = await api.run('search_central_observations', { q: 'twelve-year', limit: 5 });
  assert.equal(observationSearch.results[0].id, 'OBS-0001');
  assert.ok(dbOpens >= 4, 'catalogue database should be queried for each tool operation');
  assert.ok(queryCalls.length >= 8, 'database query path should be exercised');
  console.log('Agent-tools smoke test passed: lazy client load, Level 1 evidence lookup, Level 2 observation lookup.');
}

main().catch(err => { console.error(err); process.exitCode = 1; });
