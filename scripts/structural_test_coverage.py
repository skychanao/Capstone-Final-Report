"""Share of headers per top-level folder that are #included by at least one unit-test file."""
import os, re, sys
from collections import defaultdict

ROOT = sys.argv[1]
FOLDERS = ["core", "scene", "servers", "editor"]
INCLUDE = re.compile(r'^\s*#\s*include\s+"([^"]+\.h)"', re.M)

def walk(base, pred):
    for dirpath, _, names in os.walk(os.path.join(ROOT, base)):
        for n in names:
            if pred(n):
                yield os.path.relpath(os.path.join(dirpath, n), ROOT)

tested = set()
test_files = list(walk("tests", lambda n: n.startswith("test_")))
test_files += [p for p in walk("modules", lambda n: n.startswith("test_")) if "/tests/" in p]
for p in test_files:
    with open(os.path.join(ROOT, p), errors="ignore") as f:
        tested |= set(INCLUDE.findall(f.read()))

print(f"test files scanned: {len(test_files)}")
print("folder,headers,included_by_tests,pct")
for d in FOLDERS:
    by_sub = defaultdict(lambda: [0, 0])
    hs = list(walk(d, lambda n: n.endswith(".h") and ".gen." not in n))
    hit = [h for h in hs if h in tested]
    print(f"{d},{len(hs)},{len(hit)},{100*len(hit)/max(len(hs),1):.1f}")
    for h in hs:
        sub = "/".join(h.split("/")[:2])
        by_sub[sub][0] += 1; by_sub[sub][1] += h in tested
    for sub, (n, t) in sorted(by_sub.items()):
        print(f"    {sub},{n},{t},{100*t/n:.1f}")
