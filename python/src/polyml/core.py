"""Load, validate and derive views from polyML v0.1 documents."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from importlib import resources
from itertools import combinations
from pathlib import Path
from typing import Any

import jsonschema

CORE_RELATIONSHIP_TYPES = frozenset({"romantic", "sexual", "platonic", "queerplatonic", "chosen-family",
                                     "co-parent", "play-partner", "friend", "undefined"})
CORE_GROUP_TYPES = frozenset({"house", "pod", "polycule", "family", "other"})
CORE_DYNAMICS = frozenset({"d-s", "caregiver", "pet-play", "age-play", "switch", "fluctuating"})

Doc = dict[str, Any]


def _schema() -> dict:
    return json.loads(resources.files("polyml").joinpath("polyml.schema.json").read_text("utf-8"))


def load(path: str | Path) -> Doc:
    """Read a .polyml.json or .polyml.yaml file."""
    path = Path(path)
    text = path.read_text("utf-8")
    if path.suffix in {".yaml", ".yml"}:
        import yaml  # optional dependency
        return yaml.safe_load(text)
    return json.loads(text)


def _date_key(d: str | None, default: str) -> str:
    return (d + "-01-01")[:10] if d else default


def _vocab(doc: Doc, key: str) -> set[str]:
    return {t["id"] for t in (doc.get("vocab") or {}).get(key, [])}


def validate(doc: Doc) -> list[str]:
    """Return a list of problems; empty means the document is valid (schema + spec §9 rules)."""
    errors = [f"{'/'.join(map(str, e.absolute_path)) or '(root)'}: {e.message}"
              for e in jsonschema.Draft202012Validator(_schema()).iter_errors(doc)]
    if errors:
        return errors

    people = doc["people"]
    groups = doc.get("groups", [])
    rels = doc["relationships"]
    for kind, items in (("person", people), ("group", groups), ("relationship", rels)):
        for i, n in Counter(x["id"] for x in items).items():
            if n > 1:
                errors.append(f"duplicate {kind} id: {i}")

    pids = {p["id"] for p in people}
    gids = {g["id"] for g in groups}
    rtypes = CORE_RELATIONSHIP_TYPES | _vocab(doc, "relationship_types")
    gtypes = CORE_GROUP_TYPES | _vocab(doc, "group_types")
    dyns = CORE_DYNAMICS | _vocab(doc, "dynamics")

    for g in groups:
        if g["type"] not in gtypes:
            errors.append(f"group {g['id']}: unknown group type {g['type']!r}")
        if g.get("parent") and g["parent"] not in gids:
            errors.append(f"group {g['id']}: unknown parent {g['parent']}")
        for m in g.get("members", []):
            if m not in pids:
                errors.append(f"group {g['id']}: unknown member {m}")
    parent = {g["id"]: g.get("parent") for g in groups}
    for gid in parent:
        seen, cur = set(), gid
        while cur and cur in parent:
            if cur in seen:
                errors.append(f"group {gid}: parent chain has a cycle")
                break
            seen.add(cur)
            cur = parent[cur]

    pairs: dict[frozenset, str] = {}
    for r in rels:
        a, b = (p["person"] for p in r["parties"])
        for p in (a, b):
            if p not in pids:
                errors.append(f"relationship {r['id']}: unknown person {p}")
        if a == b:
            errors.append(f"relationship {r['id']}: both parties are {a}")
        key = frozenset((a, b))
        if key in pairs:
            errors.append(f"relationship {r['id']}: same pair as {pairs[key]}")
        pairs[key] = r["id"]
        for t in r["types"]:
            if t not in rtypes:
                errors.append(f"relationship {r['id']}: unknown type {t!r}")
        for d in r.get("dynamics", []):
            if d not in dyns:
                errors.append(f"relationship {r['id']}: unknown dynamic {d!r}")
        hist = r.get("history", [])
        for prev, nxt in zip(hist, hist[1:]):
            if _date_key(prev.get("to"), "9999-12-31") > _date_key(nxt.get("from"), "0000-01-01"):
                errors.append(f"relationship {r['id']}: history periods overlap or are out of order")
        if hist and hist[-1]["status"] != r.get("status", "active"):
            errors.append(f"relationship {r['id']}: status does not match last history period")
    return errors


def snapshot(doc: Doc, date: str | None = None) -> list[Doc]:
    """Relationships active on `date` (YYYY[-MM[-DD]]), or currently active when date is None."""
    if date is None:
        return [r for r in doc["relationships"] if r.get("status", "active") == "active"]
    d = _date_key(date, "")
    out = []
    for r in doc["relationships"]:
        hist = r.get("history")
        if hist:
            if any(h["status"] == "active" and _date_key(h.get("from"), "0000-01-01") <= d
                   < _date_key(h.get("to"), "9999-12-31") for h in hist):
                out.append(r)
        elif r.get("status", "active") == "active" and _date_key(r.get("since"), "0000-01-01") <= d:
            out.append(r)
    return out


def metamours(doc: Doc, rels: list[Doc] | None = None) -> set[frozenset]:
    """Pairs who share a partner but have no relationship of their own."""
    rels = snapshot(doc) if rels is None else rels
    partners: dict[str, set[str]] = defaultdict(set)
    linked = set()
    for r in rels:
        a, b = (p["person"] for p in r["parties"])
        partners[a].add(b)
        partners[b].add(a)
        linked.add(frozenset((a, b)))
    return {frozenset(pair) for ps in partners.values() for pair in combinations(sorted(ps), 2)} - linked


def stats(doc: Doc) -> dict[str, Any]:
    active = snapshot(doc)
    degree = Counter(p["person"] for r in active for p in r["parties"])
    return {
        "people": len(doc["people"]),
        "groups": len(doc.get("groups", [])),
        "relationships": len(doc["relationships"]),
        "active_relationships": len(active),
        "metamour_pairs": len(metamours(doc, active)),
        "types": dict(Counter(t for r in doc["relationships"] for t in r["types"])),
        "most_connected": degree.most_common(3),
    }
