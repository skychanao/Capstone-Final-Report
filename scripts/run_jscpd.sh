#!/bin/bash
# Requires a clone of Godot at commit 9c776068d6ed23acd0c78bfe534272d1d2a3a619;
# clone it first and run this script from the root of the clone.
set -e

# C++ clones of at least 100 tokens, generated files excluded
npx --yes jscpd@4.3.0 --format cpp --formats-exts "cpp:cpp,h,hpp,inc,mm" --min-tokens 100 \
    --ignore "**/*so_wrap*,**/*.gen.*" \
    --reporters json,console --output m5_jscpd \
    core servers scene editor main drivers platform modules
