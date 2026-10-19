"""Summarise lizard (M1/M2 function level) and cloc (M2 file level) output per top-level folder."""

import csv
import statistics
import sys
from collections import defaultdict

CCN_LIMIT, NLOC_LIMIT, FILE_LIMIT = 15, 100, 2000


def top(path):
    return path.lstrip("./").split("/")[0]


funcs = []  # (folder, file, function, nloc, ccn)
with open(sys.argv[1], newline="") as f:
    for r in csv.reader(f):
        if r and r[0].isdigit():  # skip header if present
            funcs.append((top(r[6]), r[6], r[7], int(r[0]), int(r[1])))

by = defaultdict(list)
for fn in funcs:
    by[fn[0]].append(fn)
print(
    "folder,functions,ccn_mean,ccn_median,ccn_p90,ccn_max,ccn_gt15,ccn_gt15_pct,nloc_gt100"
)
for folder, fs in sorted(by.items()):
    c = [x[4] for x in fs]
    hi = sum(v > CCN_LIMIT for v in c)
    print(
        f"{folder},{len(c)},{statistics.mean(c):.2f},{statistics.median(c)},"
        f"{statistics.quantiles(c, n=10)[8]:.0f},{max(c)},{hi},{100 * hi / len(c):.2f},"
        f"{sum(x[3] > NLOC_LIMIT for x in fs)}"
    )

print("\nTop 10 functions by CCN")
for fn in sorted(funcs, key=lambda x: -x[4])[:10]:
    print(f"{fn[4]:>5}  {fn[3]:>5} NLOC  {fn[1]}  {fn[2]}")

if len(sys.argv) > 2:  # cloc: language,filename,blank,comment,code
    files = defaultdict(list)
    with open(sys.argv[2], newline="") as f:
        for r in csv.reader(f):
            if len(r) >= 5 and r[4].isdigit() and r[0] != "SUM":
                files[top(r[1])].append((r[1], int(r[3]), int(r[4])))
    print("\nfolder,files,code_loc,files_gt2000,comment_density_pct")
    for folder, fs in sorted(files.items()):
        code = sum(x[2] for x in fs)
        com = sum(x[1] for x in fs)
        print(
            f"{folder},{len(fs)},{code},{sum(x[2] > FILE_LIMIT for x in fs)},"
            f"{100 * com / (com + code):.1f}"
        )
