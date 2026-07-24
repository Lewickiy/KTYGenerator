#!/usr/bin/env python3

"""PyCharm/Blender entry point for the procedural AGV generator.

Open this file in Blender's Text Editor or configure PyCharm to run Blender with
``--python main.py``.  The actual application is deliberately kept in ``src``.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Blender does not consistently add the directory of a ``--python`` script to
# ``sys.path``.  Add this file's directory explicitly so ``src`` can be
# imported even when Blender was launched from another working directory.
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

"""CLI entry point for the Procedural KTY Generator."""
from src.kty_generator.cli import main

if __name__ == "__main__":
    main()
