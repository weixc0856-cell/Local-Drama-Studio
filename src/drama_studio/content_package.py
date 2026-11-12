"""Compatibility shim: re-points to ``drama_studio.application.content_package``.

The module object is replaced, so private names and module-level state stay
shared with the implementation while the migration is in progress. New code
must import from the layer path.
"""

import importlib
import sys

_impl = importlib.import_module("drama_studio.application.content_package")
_parent_name, _, _leaf = __name__.rpartition(".")
_parent = sys.modules.get(_parent_name)
if _parent is not None:
    setattr(_parent, _leaf, _impl)
sys.modules[__name__] = _impl
