"""Command line interface: polyml validate | stats."""
from __future__ import annotations

import argparse
import json
import sys

from .core import load, stats, validate


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="polyml", description="Work with polyML files (v0.3; v0.1 and v0.2 are upgraded on read).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate", help="check files against the schema and spec rules")
    v.add_argument("files", nargs="+")
    s = sub.add_parser("stats", help="summarise a network")
    s.add_argument("file")
    a = ap.parse_args(argv)

    if a.cmd == "validate":
        bad = 0
        for f in a.files:
            errs = validate(load(f))
            print(f"{f}: {'ok' if not errs else f'{len(errs)} problem(s)'}")
            for err in errs:
                print(f"  - {err}")
            bad += bool(errs)
        return 1 if bad else 0

    doc = load(a.file)
    errs = validate(doc)
    if errs:
        print(f"{a.file} is not valid; run `polyml validate` for details", file=sys.stderr)
        return 1
    print(json.dumps(stats(doc), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
