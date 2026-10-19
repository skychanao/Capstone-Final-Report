#!/bin/bash
# Requires a clone of Godot at commit 9c776068d6ed23acd0c78bfe534272d1d2a3a619;
# clone it first and run this script from the root of the clone.
set -e

# Per-function NLOC and CCN, generated files excluded
lizard -l cpp --csv -x "*so_wrap*" -x "*.gen.*" \
    core servers scene editor main drivers platform modules \
    >m1_lizard.csv
