#!/bin/bash
# Requires a clone of Godot at commit 9c776068d6ed23acd0c78bfe534272d1d2a3a619;
# clone it first and run this script from the root of the clone.
set -e

# Per-file blank/comment/code lines, generated files excluded
cloc --by-file --csv --quiet --include-lang="C++,C/C++ Header" \
    --not-match-f='(so_wrap|\.gen\.)' \
    --report-file=m2_cloc.csv \
    core servers scene editor main drivers platform modules
