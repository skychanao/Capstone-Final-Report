#!/bin/bash
# Requires a clone of Godot at commit 9c776068d6ed23acd0c78bfe534272d1d2a3a619;
# clone it first and run this script from the root of the clone.
set -e

# Godot's bundled tool; -p adds percentages
python3 doc/tools/doc_status.py -p doc/classes modules/*/doc_classes \
    >m7_doc_status.txt

# -b: only classes that are not fully documented
python3 doc/tools/doc_status.py -p -b doc/classes modules/*/doc_classes \
    >m7_doc_status_bad.txt
