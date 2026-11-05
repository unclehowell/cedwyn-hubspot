#!/usr/bin/env python3
"""Fast regression tests for injecting the central agent tools into nested Cedwyn pages."""
import importlib.util
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("cedwyn_selfcontain", ROOT / "tools" / "selfcontain.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

evidence = '<!doctype html><html><head><title>Evidence</title></head><body>Record</body></html>'
out = mod.add_boot(evidence, "research/evidence/ev-0617-twelve-year-limitation-rule-1879-1940/index.html")
assert 'ghf-boot.js' in out, "shared header not injected"
assert '<script src="/_cedwyn/agent-tools.js?v=1" defer data-cedwyn-agent-tools></script>' in out, "nested evidence page lacks the central agent tools"
assert out.count('/_cedwyn/agent-tools.js') == 1, "agent tools script was duplicated"

home = '<!doctype html><html><head><script src="/_cedwyn/agent-tools.js" defer data-agent-footer="webmcp"></script></head><body>Home</body></html>'
home_out = mod.add_boot(home, "index.html")
assert home_out.count('/_cedwyn/agent-tools.js') == 1, "existing homepage agent script was duplicated"

resource = '<html><head><title>Blob</title></head><body>not an HTML page route</body></html>'
assert mod.add_boot(resource, "_cedwyn/agent-tools.html") == resource, "internal asset directory should be skipped"
print("Agent-loader test passed: nested evidence page gets WebMCP script; existing homepage is not duplicated.")
