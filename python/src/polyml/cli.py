"""Command line interface: polyml validate | stats | export."""
from __future__ import annotations

import argparse
import json
import sys

from .core import load, public_export, stats, validate


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="polyml", description="Work with polyML v0.1 files.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate", help="check files against the schema and spec rules")
    v.add_argument("files", nargs="+")
    s = sub.add_parser("stats", help="summarise a network")
    s.add_argument("file")
    e = sub.add_parser("export", help="write a copy safe to share")
    e.add_argument("file")
    e.add_argument("--public", action="store_true", required=True, help="apply visibility rules (spec section 7)")
    e.add_argument("-o", "--output", help="output path (default: stdout)")
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
    if a.cmd == "stats":
        print(json.dumps(stats(doc), indent=2))
        return 0
    text = json.dumps(public_export(doc), indent=2) + "\n"
    if a.output:
        with open(a.output, "w", encoding="utf-8") as fh:
            fh.write(text)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
