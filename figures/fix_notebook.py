#!/usr/bin/env python3
"""Fix Jupyter notebook widget metadata for GitHub rendering.

Colab often exports widget models directly under:
  metadata.widgets["application/vnd.jupyter.widget-state+json"]

GitHub expects them nested one level deeper:
  metadata.widgets["application/vnd.jupyter.widget-state+json"]["state"]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

WIDGET_MIME = "application/vnd.jupyter.widget-state+json"


def fix_widgets_metadata(nb: dict, *, remove_widgets: bool = False) -> bool:
    """Return True if notebook metadata was modified."""
    metadata = nb.setdefault("metadata", {})
    widgets = metadata.get("widgets")
    if not widgets:
        return False

    if remove_widgets:
        del metadata["widgets"]
        return True

    if WIDGET_MIME in widgets:
        mime_block = widgets[WIDGET_MIME]
        if isinstance(mime_block, dict) and "state" in mime_block:
            return False

        models = {
            key: value
            for key, value in mime_block.items()
            if key not in {"state", "version_major", "version_minor"}
        }
        metadata["widgets"] = {
            WIDGET_MIME: {
                "state": models,
                "version_major": mime_block.get("version_major", 2),
                "version_minor": mime_block.get("version_minor", 0),
            }
        }
        return True

    if "state" in widgets:
        metadata["widgets"] = {
            WIDGET_MIME: {
                "state": widgets["state"],
                "version_major": widgets.get("version_major", 2),
                "version_minor": widgets.get("version_minor", 0),
            }
        }
        return True

    return False


def fix_notebook(path: Path, out_path: Path, *, remove_widgets: bool = False) -> bool:
    nb = json.loads(path.read_text(encoding="utf-8"))
    if not fix_widgets_metadata(nb, remove_widgets=remove_widgets):
        return False

    out_path.write_text(
        json.dumps(nb, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return True


def iter_notebooks(target: Path) -> list[Path]:
    if target.is_file():
        return [target]
    return sorted(target.rglob("*.ipynb"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path, help="Notebook file or directory")
    parser.add_argument(
        "--output",
        type=Path,
        help="Write the fixed notebook to this path (single input file only)",
    )
    parser.add_argument(
        "--remove-widgets",
        action="store_true",
        help="Delete metadata.widgets entirely instead of converting it",
    )
    args = parser.parse_args(argv)

    if args.output and len(args.paths) != 1:
        parser.error("--output can only be used with a single notebook file")

    for path_arg in args.paths:
        if not path_arg.exists():
            print(f"Skipping missing path: {path_arg}", file=sys.stderr)
            continue

        notebooks = iter_notebooks(path_arg)
        if args.output and len(notebooks) != 1:
            parser.error("--output requires a single notebook file as input")

        for notebook in notebooks:
            out_path = args.output if args.output else notebook
            if fix_notebook(notebook, out_path, remove_widgets=args.remove_widgets):
                if out_path == notebook:
                    print(f"Fixed {notebook}")
                else:
                    print(f"Fixed {notebook} -> {out_path}")
            else:
                print(f"No changes needed: {notebook}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
