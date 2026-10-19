"""NOM(virtual) of a base class, its 'not supported' stubs, and per-subclass override ratio."""
import re, sys

cls, base_h, base_cpp, *subs = sys.argv[1:]
VIRTUAL = re.compile(r"^\s*virtual\s+[^;(]*?\b(\w+)\s*\(", re.M)
OVERRIDE = re.compile(r"(\w+)\s*\([^;{]*?\)\s*(?:const\s*)?override")
STUB = re.compile(r"not (?:supported|implemented)", re.I)

def text(p):
    with open(p, errors="ignore") as f:
        return f.read()

virtuals = set(VIRTUAL.findall(text(base_h))) - {"~" + cls, cls}

stubs, src = set(), text(base_cpp)            # find "Cls::name(...) ... {" and scan body
for m in re.finditer(rf"\b{cls}::(\w+)\s*\(", src):
    name, i = m.group(1), src.find("{", m.end())
    if name not in virtuals or i < 0 or ";" in src[m.end():i]:
        continue
    depth, j = 0, i
    while j < len(src):
        depth += src[j] == "{"; depth -= src[j] == "}"
        if depth == 0:
            break
        j += 1
    if STUB.search(src[i:j]):
        stubs.add(name)

n = len(virtuals)
print(f"{cls}: NOM(virtual)={n}, stubs={len(stubs)} ({100*len(stubs)/n:.1f}%)")
print("subclass,overridden,override_ratio_pct")
for h in subs:
    o = set(OVERRIDE.findall(text(h))) & virtuals
    print(f"{h},{len(o)},{100*len(o)/n:.1f}")
print("\nStubbed methods:", ", ".join(sorted(stubs)))
