"""Regression tests for the page-journal key exemption in tools/agent_lint.py.
Self-contained: synthetic inputs only; loads the repo's own tools/agent_lint.py.
Run from the repo root:  python3 -m unittest tests/test_agent_lint_journal.py
Override the module path with AGENT_LINT=/path/to/agent_lint.py."""
import copy, importlib.util, json, os, pathlib, subprocess, sys, tempfile, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
MOD = pathlib.Path(os.environ.get('AGENT_LINT') or ROOT / 'tools' / 'agent_lint.py')
spec = importlib.util.spec_from_file_location('agent_lint', MOD)
L = importlib.util.module_from_spec(spec); spec.loader.exec_module(L)
J = 'data/journal/pages.json'
FRAUD_KEY = '/research/scrutiny-and-accountability/legal-review-fraud-land-human-rights/'

def base():
    return {'schema': 'cedwyn-page-journal/1.0', 'note': 'Neutral, dated change lines per page.',
            'pages': {'/': [{'v': 'update', 'date': '2026-10-30', 'note': 'Front page updated.'}],
                      '/academy/FLYWHEELS/': [{'v': 'update', 'date': '2026-10-30', 'note': 'Entry.', 'agent': 'Tab'}],
                      FRAUD_KEY: [{'v': 'update', 'date': '2026-10-30', 'note': 'References now name the holding bodies.'}]}}
def dump(d): return json.dumps(d, indent=1, ensure_ascii=False)
def banned(out): return [x for x in out if ': banned word:' in x]

class JournalLint(unittest.TestCase):
    def test_the_original_false_positive_is_real(self):
        key_line = '  "%s": [' % FRAUD_KEY
        self.assertTrue(L.CHECKS[0][0] == 'banned word' and L.CHECKS[0][1].search(key_line))

    def test_synthetic_file_with_fraud_key_passes(self):
        self.assertEqual(L.lint(J, dump(base())), [])

    def test_clean_new_entry_passes(self):
        d = base(); d['pages']['/directory/p/x/'] = [{'v': 'update', 'date': '2026-10-31', 'note': 'History line added.'}]
        self.assertEqual(L.lint(J, dump(d)), [])

    def test_banned_words_in_values_still_fail(self):
        for w in ('fraud', 'alleged', 'claims', 'hearsay', 'stolen'):
            d = base(); d['pages'][FRAUD_KEY][0]['note'] = 'A %s was noted.' % w
            self.assertTrue(banned(L.lint(J, dump(d))), w)
        d = base(); d['pages'][FRAUD_KEY][0]['agent'] = 'fraud'
        self.assertTrue(banned(L.lint(J, dump(d))))
        d = base(); d['note'] += ' alleged'
        self.assertTrue(banned(L.lint(J, dump(d))))

    def test_odd_key_wrong_shape_or_malformed_falls_back(self):
        d = base(); d['pages']['/Bad Key fraud/'] = d['pages'].pop(FRAUD_KEY)
        self.assertTrue(banned(L.lint(J, dump(d))))
        d = base(); d['extra'] = 1
        self.assertTrue(banned(L.lint(J, dump(d))))
        d = base(); d['pages'][FRAUD_KEY][0]['surprise'] = 'x'
        self.assertTrue(banned(L.lint(J, dump(d))))
        d = base(); d['pages'][FRAUD_KEY][0]['note'] = 5
        self.assertTrue(banned(L.lint(J, dump(d))))
        self.assertTrue(banned(L.lint(J, dump(base())[:-3])))

    def test_other_paths_unchanged(self):
        for p in ('data/other.json', 'reports/pages.json', 'data/journal/other.json'):
            self.assertTrue(banned(L.lint(p, dump(base()))), p)
        self.assertTrue(banned(L.lint('research/page.html', '<p>A fraud claim. EV-0001</p>')))

    def test_other_checks_read_the_original_line_in_the_journal(self):
        d = base(); d['pages'][FRAUD_KEY][0]['note'] = 'See [x](https://example.org/x).'
        self.assertTrue(any('outbound link' in x for x in L.lint(J, dump(d))))
        d = base(); d['pages'][FRAUD_KEY][0]['note'] = 'Years 1547 noted.'
        self.assertTrue(any('pre-1824' in x for x in L.lint(J, dump(d))))
        d = base(); d['pages'][FRAUD_KEY][0]['note'] = 'Mail a@b.org'
        self.assertTrue(any('email address' in x for x in L.lint(J, dump(d))))

    def test_cli_exit_codes(self):
        with tempfile.TemporaryDirectory() as t:
            (pathlib.Path(t) / 'data/journal').mkdir(parents=True)
            f = pathlib.Path(t) / J
            f.write_text(dump(base()), 'utf-8')
            r = subprocess.run([sys.executable, str(MOD), '--root', t, J], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            d = base(); d['pages'][FRAUD_KEY][0]['note'] = 'alleged'
            f.write_text(dump(d), 'utf-8')
            r = subprocess.run([sys.executable, str(MOD), '--root', t, J], capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)

if __name__ == '__main__': unittest.main(verbosity=2)
