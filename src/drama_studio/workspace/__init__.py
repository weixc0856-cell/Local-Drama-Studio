"""Local production workspace (backend + static UI).

The workspace never invents production state. Everything shown in the UI is
derived from real files on disk or from task records written when a real
command actually ran.
"""

from .store import WorkspaceStore, get_store

__all__ = ["WorkspaceStore", "get_store"]
