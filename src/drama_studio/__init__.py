"""Local-Drama-Studio orchestration package.

The root ``.venv`` only ever contains orchestration dependencies. Torch,
PyTorch-XPU and ComfyUI live in ``runtime/ComfyUI/.venv`` and are never
imported from this package.
"""

__version__ = "0.1.0"
