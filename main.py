"""Chromecast Remote Control - Application Entry Point.

This root script serves as the primary entry point, allowing users to launch
the application directly from the project root via:
    python main.py
"""
import os
import sys

_project_root = os.path.dirname(os.path.abspath(__file__))
_src_dir = os.path.join(_project_root, "src")

if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)
if _project_root not in sys.path:
    sys.path.insert(1, _project_root)

from src.main import run_app, main, config, prevent_multiple_instances

if __name__ == "__main__":
    run_app()
