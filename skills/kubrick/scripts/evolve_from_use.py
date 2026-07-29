#!/usr/bin/env python3
"""
Thin wrapper for kubrick evolution.

Prefers the installed optional extra:
  pip install continuity-forge[kubrick-helpers]

Falls back to bundled logic when the extra is not installed.
"""

import sys
import os

try:
    from kubrick_helpers.evolution import main as _main
    if __name__ == "__main__":
        _main()
except ImportError:
    print("kubrick-helpers not installed. Using bundled version from the skill.", file=sys.stderr)
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    SKILL_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
    sys.path.insert(0, SKILL_ROOT)

    exec(open(os.path.join(SCRIPT_DIR, "_evolve_impl.py")).read())
