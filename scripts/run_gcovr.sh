#!/bin/bash
# Requires a clone of Godot at commit 9c776068d6ed23acd0c78bfe534272d1d2a3a619;
# clone it first and run this script from the root of the clone.

# Exit immediately if a command exits with a non-zero status
set -e

# Build Godot (expect 1–3 hours; -j6 keeps RAM below 15 GB)
scons platform=linuxbsd target=editor dev_build=yes tests=yes use_coverage=yes -j6

# Run tests and log output
bin/godot.linuxbsd.editor.dev.x86_64 --test --headless 2>&1 |
    tee m6_tests.log

# Generate coverage reports
for d in core scene servers; do
    gcovr --root . --filter "$d/" --exclude 'thirdparty/' --exclude 'tests/' \
        --gcov-ignore-parse-errors -j 8 --print-summary \
        --csv "m6_$d.csv" >"m6_$d.txt"
done

echo "Build, tests, and coverage generation complete."
