#!/usr/bin/env python3
"""
Thin wrapper for kubrick retrieval.

Prefers the installed optional extra:
  pip install continuity-forge[kubrick-helpers]

Falls back to bundled logic when the extra is not installed
(works when the skill is simply copied to ~/.hermes/skills/).

See also: kubrick-retrieve (CLI installed by the extra)
"""

import sys
import os

try:
    from kubrick_helpers.retrieval import main as _main
    if __name__ == "__main__":
        _main()
except ImportError:
    # Standalone / pure skill copy fallback
    print("kubrick-helpers not installed. Using bundled version from the skill.", file=sys.stderr)
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    SKILL_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
    sys.path.insert(0, SKILL_ROOT)  # allow relative imports if needed

    # Execute the original bundled implementation
    # (kept in this file below for maximum standalone compatibility)
    exec(open(os.path.join(SCRIPT_DIR, "_retrieve_impl.py")).read())
