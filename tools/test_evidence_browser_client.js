#!/usr/bin/env node
'use strict';

/* Cold-load test for web/_cedwyn/evidence-browser.js (30 Oct 2026).
   The page markup never includes /_cedwyn/cat.js; the catalogue view must load
   the client itself before its first read. Simulates a cold page (window.Cedwyn
   absent), lets the injected script resolve asynchronously, and asserts the
   catalogue renders - including a CSSCPSG block - plus the designed degradation
   when the client load genuinely fails. No timers in the code under test. */

const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

const source = fs.readFileSync(path.join(__dirname, '..', 'web', '_cedwyn', 'evidence-browser.js'), 'utf8');
assert.ok(!/setTimeout|setInterval/.test(source.match(/function clientReady[\s\S]*?\n  \}/)[0]),
  'clientReady must await the script load event, never a timer');

function element(tag) {
  return {
    tagName: tag.toUpperCase(), children: [], className: '', textContent: '',
    id: '', hidden: false, value: '', href: '', src: '', async: false,
    onload: null, onerror: null, listeners: {},
    setAttribute(k, v) { (this.attrs = this.attrs || {})[k] = String(v); },
    getAttribute(k) { return (this.attrs || {})[k] || null; },
    appendChild(child) { this.children.push(child); return child; },
    replaceChildren() { this.children = []; },
    addEventListener(type, fn) { (this.listeners[type] = this.listeners[type] || []).push(fn); },
    querySelector() { return null; }, querySelectorAll() { return []; }
  };
}

function findAll(node, pred, out) {
  out = out || [];
  (node.children || []).forEach(c => { if (pred(c)) out.push(c); findAll(c, pred, out); });
  return out;
}

const row = {
  ev: 'EV-0001', title: '1955 possession order entry', path: '/research/evidence/ev-0001-order/',
  evidence_grade: 2, independent_origin_id: 'origin-1955-order', grade_note: 'Known through a later judgment.',
  aliases_json: '[]', description: 'Neutral record description.', description_status: 'assessed',
  transcript: '', transcript_status: 'not_assessed',
  interpretation: 'Interpretation kept separate.', interpretation_status: 'assessed',
  source_verification_status: 'reviewed', limitations: 'Underlying order copy not independently inspected.',
  csscpsg_json: JSON.stringify({
    schema: 'csscpsg/1',
    scores: { S1: 1, S2: 2, S3: 0, S4: 1, S5: 2, S6: 0 },
    why: { S1: 'Recited as covering the whole of the farm.' },
    timing: [{ event: 'Notice to quit expired 2 Feb 1955', score: 0, why: 'Yearly tenancy anniversary: explained.' }],
    result: { compliant: true, S: 6, T: 0, D: 6 }
  }),
  catalogue_page_text: 'Published catalogue entry text.', catalogue_text_truncated: 0
};

function buildContext(opts) {
  const window = {};
  const state = { clientLoads: 0, queries: [] };
  const db = {
    query: async (sql) => {
      state.queries.push(sql);
      if (sql.includes('pragma_table_info')) return [{ name: 'ev' }, { name: 'csscpsg_json' }];
      if (sql.includes('SUM(CASE WHEN')) return [{ total: 1, described: 1, transcribed: 0, interpreted: 1 }];
      if (sql.includes('FROM evidence_catalogue ec')) return [row];
      return [];
    }
  };
  const registry = {};
  ['[data-status]', '[data-results]', '#cw-eb-query', '[data-more]', '[data-coverage]', 'form', '[data-reset]']
    .forEach(sel => { registry[sel] = element(sel === 'form' ? 'form' : 'div'); });
  const modeButtons = [element('button'), element('button')];
  const root = element('section');
  root.querySelector = sel => registry[sel] || null;
  root.querySelectorAll = sel => (sel === '[data-mode]' ? modeButtons : []);
  const document = {
    readyState: 'loading',
    head: element('head'), documentElement: element('html'),
    querySelector: sel => (sel === '[data-cedwyn-evidence-browser]' ? root : null),
    createElement: element
  };
  const realAppend = document.head.appendChild.bind(document.head);
  document.head.appendChild = script => {
    assert.equal(script.src, '/_cedwyn/cat.js', 'must load the catalogue client URL');
    state.clientLoads++;
    setTimeout(() => {
      if (opts.clientSucceeds) {
        window.Cedwyn = { db: async () => db, sectionDb: async () => db };
        script.onload && script.onload();
      } else {
        script.onerror && script.onerror();
      }
    }, 0);
    return realAppend(script);
  };
  window.document = document;
  const context = { window, document, navigator: {}, console, URL, JSON, Promise, setTimeout, clearTimeout };
  vm.runInNewContext(source, context, { filename: 'evidence-browser.js' });
  return { window, document, root, registry, state };
}

async function flush(times) {
  for (let i = 0; i < (times || 8); i++) await new Promise(r => setTimeout(r, 0));
}

async function main() {
  // Cold load, client fetch succeeds: the view must render without any click.
  const ok = buildContext({ clientSucceeds: true });
  await flush();
  assert.equal(ok.state.clientLoads, 1, 'exactly one client script injection');
  const status = ok.registry['[data-status]'].textContent;
  assert.ok(status.startsWith('Level 1 · Artifacts'), 'cold load should render artifacts, got: ' + status);
  assert.ok(status.includes('Wiki section database'), 'theme slice source should be named, got: ' + status);
  const results = ok.registry['[data-results]'];
  assert.equal(results.children.length, 1, 'one record card rendered');
  const csBoxes = findAll(results, n => (n.className || '').includes('cw-eb-csscpsg'));
  assert.equal(csBoxes.length, 1, 'the record renders its CSSCPSG block');
  const s1 = findAll(csBoxes[0], n => (n.textContent || '').startsWith('S1 Scope: 1'));
  assert.equal(s1.length, 1, 'S1 score line rendered with reasoning');
  assert.ok(ok.registry['[data-coverage]'].textContent.includes('1 records'), 'coverage line populated');

  // Genuine client failure: the designed degradation must survive.
  const bad = buildContext({ clientSucceeds: false });
  await flush();
  assert.equal(bad.state.clientLoads, 1, 'one injection attempt before failing');
  assert.ok(bad.registry['[data-status]'].textContent.startsWith('Could not read the catalogue:'),
    'failure keeps the designed status, got: ' + bad.registry['[data-status]'].textContent);
  const retry = findAll(bad.registry['[data-results]'],
    n => (n.textContent || '').includes('The source register remains below'));
  assert.equal(retry.length, 1, 'retry guidance still offered on genuine failure');

  console.log('test_evidence_browser_client: OK (cold load renders incl. CSSCPSG; genuine failure degrades as designed)');
}

main().catch(err => { console.error(err); process.exit(1); });
