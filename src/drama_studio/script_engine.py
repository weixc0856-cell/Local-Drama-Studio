"""Compatibility shim: re-points to ``drama_studio.application.script_engine``.

The module object is replaced, so private names and module-level state
stay shared with the implementation while the migration is in progress.
New code must import from the layer path.
"""

import importlib
import sys

sys.modules[__name__] = importlib.import_module("drama_studio.application.script_engine")
