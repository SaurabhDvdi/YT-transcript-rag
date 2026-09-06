"""Cloudflare Worker entrypoint for Python backend."""

import os
import sys
import types

_current_dir = os.path.dirname(os.path.abspath(__file__))
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

# Shim 'src' package namespace for Pyodide Workers runtime
if "src" not in sys.modules:
    _src_shim = types.ModuleType("src")
    _src_shim.__path__ = [_current_dir]
    sys.modules["src"] = _src_shim

from src.main import app  # noqa: E402

try:
    from workers import asgi

    # Official workers-py entrypoint pattern
    Default = asgi.entrypoint(app)

except (ImportError, ModuleNotFoundError):
    # Standalone / non-Pyodide environment fallback
    class Default:  # type: ignore[no-redef]
        """Fallback for non-Workers runtime environments."""

        pass
