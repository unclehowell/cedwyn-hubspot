#!/usr/bin/env node
'use strict';

// End-to-end browser mock: register the real bundle through document.modelContext,
// verify tool discovery, then call the registered evidence-read tool.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

async function main() {
  const source = fs.readFileSync(path.join(__dirname, '..', 'web', '_cedwyn', 'agent-tools.js'), 'utf8');
  const registered = [];
  const queries = [];
  let clientLoads = 0;
  const record = {
    ev: 'EV-0001', artifact_id: 1, path: '/research/evidence/ev-0001/',
    evidence_grade: 2, independent_origin_id: 'origin-1', aliases_json: '["GHF-E001"]',
    grade_note: 'Judgment recital; primary instrument not independently inspected.',
    title: 'Test evidence entry', record_text: 'Full published entry text.',
    body_chars: 25, truncated: 0, sha: 'test-sha', kind: 'page', mime: 'text/html',
    bytes: 100, year_min: 1955, year_max: 1955, description: 'Description',
    description_status: 'assessed', transcript: '', transcript_status: 'not_assessed',
    interpretation: 'Interpretation kept separate.', interpretation_status: 'assessed',
    source_verification_status: 'reviewed', limitations: 'Primary instrument not inspected.'
  };
  const db = {
    query: async (sql, params) => {
      queries.push({ sql, params });
      if (sql.includes('FROM evidence_catalogue ec') && sql.includes('et.body AS record_text')) return [record];
      if (sql.includes('SELECT meaning FROM evidence_grade_scale')) return [{ meaning: 'Record quotes a later judgment.' }];
      return [];
    }
  };
  const window = {};
  const elements = new Map();
  function element(tag) {
    return {
      tagName: String(tag).toUpperCase(), attrs: {}, children: [], id: '',
      setAttribute(k, v) { this.attrs[k] = String(v); },
      getAttribute(k) { return this.attrs[k] || null; },
      appendChild(child) { this.children.push(child); if (child.id) elements.set(child.id, child); return child; },
      textContent: '', hidden: false
    };
  }
  const quietConsole = { warn() {}, error() {}, log() {} };
  const document = {
    readyState: 'complete', title: 'Cedwyn WebMCP smoke test',
    body: element('body'), documentElement: element('html'),
    createElement: element,
    getElementById(id) { return elements.get(id) || null; },
    head: {
      appendChild(script) {
        assert.equal(script.src, '/_cedwyn/cat.js');
        clientLoads++;
        window.Cedwyn = {
          db: () => Promise.resolve(db),
          graphql: () => Promise.resolve({ data: { search: [] } })
        };
        if (typeof script.onload === 'function') script.onload();
        return script;
      }
    },
    modelContext: {
      registerTool: async tool => { registered.push(tool); },
      getTools: async () => registered.map(tool => ({ name: tool.name }))
    }
  };
  window.document = document;
  const location = {
    href: 'https://cedwyn.bucklerfamily.estate/research/evidence/ev-0001/',
    origin: 'https://cedwyn.bucklerfamily.estate',
    pathname: '/research/evidence/ev-0001/'
  };
  vm.runInNewContext(source, {
    window, document, navigator: {}, location, URL, console: quietConsole,
    fetch: async () => ({ ok: true, headers: { get: () => 'text/plain' }, text: async () => '' }),
    setTimeout, clearTimeout
  }, { filename: 'agent-tools.js' });
  await new Promise(resolve => setTimeout(resolve, 0));

  const status = window.__cedwynWebMCP;
  assert.equal(status.api, 'document.modelContext');
  assert.equal(status.verified, true);
  assert.equal(status.registered, true);
  assert.equal(registered.length, 16, 'all sixteen tools must register');
  for (const name of [
    'get_cedwyn_flow_watch_health',
    'get_cedwyn_flow_watch_events',
    'get_cedwyn_flow_watch_contract'
  ]) {
    assert.ok(registered.some(tool => tool.name === name), name + ' must be registered');
  }
  assert.equal(clientLoads, 0, 'catalogue client must load only when called');

  const tool = registered.find(item => item.name === 'get_central_evidence_record');
  assert.ok(tool, 'central evidence read tool should be registered');
  const result = await tool.execute({ key: 'EV-0001' }, {});
  assert.equal(result.found, true);
  assert.equal(result.record.ev, 'EV-0001');
  assert.equal(result.record.sourcePageText, 'Full published entry text.');
  assert.equal(result.record.assessment.interpretation, 'Interpretation kept separate.');
  assert.equal(clientLoads, 1, 'registered tool should lazy-load the catalogue client');
  assert.ok(queries.length >= 5, 'registered tool must issue central database queries');
  console.log('WebMCP smoke test passed: 16 registered and verified, including three flow-watch resources; Level 1 record read through registered tool.');
}
main().catch(err => { console.error(err); process.exitCode = 1; });
