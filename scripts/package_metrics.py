"""Martin package metrics (Ca, Ce, I) and SDP/layer violations from #include directives."""
import os, re, sys
from collections import defaultdict

ROOT = sys.argv[1]
PKGS = ["core", "servers", "scene", "editor", "main", "drivers", "platform", "modules"]
DOC_RANK = {"core": 0, "servers": 1, "scene": 2, "editor": 3}   # layering per Godot docs
EXTS = (".h", ".cpp", ".hpp", ".c", ".m", ".mm", ".inc")
INCLUDE = re.compile(r'^\s*#\s*include\s+"([^"/]+)/')

edges = defaultdict(set)            # (src_pkg, dst_pkg) -> files in src including dst
for pkg in PKGS:
    for dirpath, _, names in os.walk(os.path.join(ROOT, pkg)):
        for name in names:
            if not name.endswith(EXTS):
                continue
            path = os.path.relpath(os.path.join(dirpath, name), ROOT)
            with open(os.path.join(ROOT, path), errors="ignore") as f:
                for line in f:
                    m = INCLUDE.match(line)
                    if m and m.group(1) in PKGS and m.group(1) != pkg:
                        edges[(pkg, m.group(1))].add(path)

ca = {p: set() for p in PKGS}       # files outside p that depend on p
ce = {p: set() for p in PKGS}       # files inside p that depend on something outside
for (src, dst), files in edges.items():
    ca[dst] |= files
    ce[src] |= files
inst = {p: len(ce[p]) / (len(ca[p]) + len(ce[p])) if ca[p] or ce[p] else 0.0 for p in PKGS}

print("package,Ca,Ce,I")
for p in sorted(PKGS, key=inst.get):
    print(f"{p},{len(ca[p])},{len(ce[p])},{inst[p]:.2f}")

print("\nSDP violations (src -> dst where I(dst) > I(src)), files")
for (src, dst), files in sorted(edges.items()):
    if inst[dst] > inst[src]:
        print(f"{src} ({inst[src]:.2f}) -> {dst} ({inst[dst]:.2f}): {len(files)}")

print("\nUpward includes against the documented layering, files")
for (src, dst), files in sorted(edges.items()):
    if src in DOC_RANK and dst in DOC_RANK and DOC_RANK[src] < DOC_RANK[dst]:
        print(f"{src} -> {dst}: {len(files)}")
        for f in sorted(files):
            print(f"    {f}")
