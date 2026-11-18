"""Load, upgrade, validate and derive views from polyML documents (v0.3; v0.1 and v0.2 are upgraded on read)."""
from __future__ import annotations

import copy
import json
from collections import Counter, defaultdict
from importlib import resources
from itertools import combinations
from pathlib import Path
from typing import Any

import jsonschema

SUPPORTED_VERSIONS = ("0.1", "0.2", "0.3")
CURRENT_VERSION = "0.3"
CORE_RELATIONSHIP_TYPES = frozenset({"romantic", "sexual", "platonic", "queerplatonic", "chosen-family",
                                     "co-parent", "play-partner", "friend", "undefined"})
CORE_GROUP_TYPES = frozenset({"house", "pod", "polycule", "family", "triad", "quad", "other"})
RA = "relationship-anarchy"

Doc = dict[str, Any]
_LOW, _HIGH = "0000-01-01", "9999-12-31"


def _schema() -> dict:
    return json.loads(resources.files("polyml").joinpath("polyml.schema.json").read_text("utf-8"))


def load(path: str | Path) -> Doc:
    """Read a .polyml.json file."""
    return json.loads(Path(path).read_text("utf-8"))


def _date_key(d: str | None, default: str) -> str:
    return (d + "-01-01")[:10] if d else default


def _vocab(doc: Doc, key: str) -> set[str]:
    return {t["id"] for t in (doc.get("vocab") or {}).get(key, [])}


def _covers(frm: str | None, to: str | None, d: str) -> bool:
    return _date_key(frm, _LOW) <= d < _date_key(to, _HIGH)


# ---------------------------------------------------------------- accessors

def membership(entry: str | Doc) -> Doc:
    """Normalise a group member entry (plain id or object) to {person, from?, to?, role?}."""
    return {"person": entry} if isinstance(entry, str) else entry


def style_of(doc: Doc, person_id: str) -> str | None:
    """A person's effective style: their own, else the document's."""
    p = next((p for p in doc["people"] if p["id"] == person_id), {})
    return p.get("style") or (doc.get("meta") or {}).get("style")


def is_anarchic(doc: Doc, rel: Doc) -> bool:
    """True when relationship-anarchy rules apply to a relationship (either party follows RA)."""
    return any(style_of(doc, p["person"]) == RA for p in rel["parties"])


def distance_of(rel: Doc) -> str | None:
    return rel.get("distance") or ("nesting" if rel.get("nesting") else None)


def is_obscured(doc: Doc, rel: Doc) -> bool:
    """True when camera obscura (spec §8) applies: either party has obscura set."""
    obscured = {p["id"] for p in doc["people"] if p.get("obscura")}
    return any(p["person"] in obscured for p in rel["parties"])


_SWITCHING = {"switch", "fluctuating"}


def upgrade(doc: Doc) -> Doc:
    """Return a copy of a v0.1/v0.2 document upgraded to v0.3 (spec §11). v0.3 documents come back unchanged.

    `dynamics` move into `tags` (switch/fluctuating also set direction "both"); `closeness` is dropped.
    """
    doc = copy.deepcopy(doc)
    if doc.get("polyml") not in ("0.1", "0.2"):
        return doc
    doc["polyml"] = CURRENT_VERSION
    vocab = doc.get("vocab")
    if isinstance(vocab, dict):
        vocab.pop("dynamics", None)
        if not vocab:
            del doc["vocab"]
    for bond in [*doc.get("relationships", []), *doc.get("groups", [])]:
        if not isinstance(bond, dict):
            continue
        dyns = list(bond.pop("dynamics", None) or [])
        for h in bond.get("history", []) or []:
            if isinstance(h, dict):
                dyns += h.pop("dynamics", None) or []
        bond.pop("closeness", None)
        if dyns:
            tags = bond.setdefault("tags", [])
            for d in dyns:
                if d not in tags:
                    tags.append(d)
            if "parties" in bond and _SWITCHING & set(dyns):
                bond.setdefault("direction", "both")
    return doc


def obscure(doc: Doc) -> Doc:
    """Return a copy where every relationship under camera obscura keeps only its id, parties and status."""
    out = copy.deepcopy(doc)
    rels = []
    for r in out["relationships"]:
        if is_obscured(out, r):
            r = {"id": r["id"], "parties": [{"person": p["person"]} for p in r["parties"]], "types": [],
                 **({"status": r["status"]} if "status" in r else {})}
        rels.append(r)
    out["relationships"] = rels
    return out


def _period_at(bond: Doc, d: str) -> Doc | None:
    for h in bond.get("history", []):
        if _covers(h.get("from"), h.get("to"), d):
            return h
    return None


def status_at(bond: Doc, date: str | None = None) -> str | None:
    """Status of a relationship or group on `date`, or now. None if it hadn't started yet."""
    if date is None:
        return bond.get("status", "active")
    d = _date_key(date, "")
    hist = bond.get("history")
    if hist:
        h = _period_at(bond, d)
        if h:
            return h["status"]
        return None if _date_key(hist[0].get("from"), _LOW) > d else bond.get("status", "active")
    if bond.get("since") and _date_key(bond["since"], _LOW) > d:
        return None
    return bond.get("status", "active")


def types_at(bond: Doc, date: str | None = None) -> list[str]:
    """Relationship types in force on `date` (history period types win), or now."""
    if date is not None:
        h = _period_at(bond, _date_key(date, ""))
        if h and "types" in h:
            return h["types"]
    return bond.get("types", [])


def direction_at(rel: Doc, date: str | None = None) -> str | None:
    """Direction in force on `date` (a party's person id or "both"), or now; None when there is none."""
    if date is not None:
        h = _period_at(rel, _date_key(date, ""))
        if h and "direction" in h:
            return h["direction"]
    return rel.get("direction")


def members_at(group: Doc, date: str | None = None) -> list[str]:
    """Person ids in a group on `date`; with no date, current members (no `to`, or `to` in the future is unknown)."""
    out = []
    for m in map(membership, group.get("members", [])):
        if date is None:
            if "to" not in m:
                out.append(m["person"])
        elif _covers(m.get("from"), m.get("to"), _date_key(date, "")):
            out.append(m["person"])
    return out


# ---------------------------------------------------------------- validation

def _check_bond(errors: list[str], label: str, bond: Doc, terms: set[str]) -> None:
    for t in bond.get("types", []):
        if t not in terms:
            errors.append(f"{label}: unknown type {t!r}")
    hist = bond.get("history", [])
    for h in hist:
        for t in h.get("types", []):
            if t not in terms:
                errors.append(f"{label}: unknown type {t!r} in history")
    for prev, nxt in zip(hist, hist[1:]):
        if _date_key(prev.get("to"), _HIGH) > _date_key(nxt.get("from"), _LOW):
            errors.append(f"{label}: history periods overlap or are out of order")
    if hist and hist[-1]["status"] != bond.get("status", "active"):
        errors.append(f"{label}: status does not match last history period")
    if hist and bond.get("since") and hist[0].get("from") and bond["since"] != hist[0]["from"]:
        errors.append(f"{label}: since ({bond['since']}) differs from the first history period ({hist[0]['from']})")


def validate(doc: Doc) -> list[str]:
    """Return a list of problems; empty means the document is valid (schema + spec §10 rules).

    v0.1 and v0.2 documents are upgraded first (see `upgrade`), so problems refer to the upgraded form.
    """
    doc = upgrade(doc)
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

    for key, core in (("relationship_types", CORE_RELATIONSHIP_TYPES), ("group_types", CORE_GROUP_TYPES)):
        for t in _vocab(doc, key) & core:
            errors.append(f"vocab.{key}: {t!r} repeats a core term")

    pids = {p["id"] for p in people}
    gids = {g["id"] for g in groups}
    rtypes = CORE_RELATIONSHIP_TYPES | _vocab(doc, "relationship_types")
    gtypes = CORE_GROUP_TYPES | _vocab(doc, "group_types")

    for g in groups:
        label = f"group {g['id']}"
        if g["type"] not in gtypes:
            errors.append(f"{label}: unknown group type {g['type']!r}")
        if g.get("parent") and g["parent"] not in gids:
            errors.append(f"{label}: unknown parent {g['parent']}")
        seen = Counter()
        for m in map(membership, g.get("members", [])):
            seen[m["person"]] += 1
            if m["person"] not in pids:
                errors.append(f"{label}: unknown member {m['person']}")
            if m.get("from") and m.get("to") and _date_key(m["from"], _LOW) >= _date_key(m["to"], _HIGH):
                errors.append(f"{label}: membership of {m['person']} ends before it starts")
        for pid, n in seen.items():
            if n > 1:
                errors.append(f"{label}: {pid} is listed more than once")
        _check_bond(errors, label, g, rtypes)
    parent = {g["id"]: g.get("parent") for g in groups}
    for gid in parent:
        visited, cur = set(), gid
        while cur and cur in parent:
            if cur in visited:
                errors.append(f"group {gid}: parent chain has a cycle")
                break
            visited.add(cur)
            cur = parent[cur]

    pairs: dict[frozenset, str] = {}
    for r in rels:
        label = f"relationship {r['id']}"
        a, b = (p["person"] for p in r["parties"])
        for p in (a, b):
            if p not in pids:
                errors.append(f"{label}: unknown person {p}")
        if a == b:
            errors.append(f"{label}: both parties are {a}")
        key = frozenset((a, b))
        if key in pairs:
            errors.append(f"{label}: same pair as {pairs[key]}")
        pairs[key] = r["id"]
        if a in pids and b in pids:
            ra = is_anarchic(doc, r)
            if ra and "priority" in r:
                errors.append(f"{label}: priority is not used under relationship anarchy")
            if not ra and not r["types"] and not is_obscured(doc, r):
                errors.append(f"{label}: needs at least one type (only relationship anarchy or camera obscura allows none)")
        for where, h in (("", r), *((" in history", h) for h in r.get("history", []))):
            if "direction" in h and h["direction"] not in (a, b, "both"):
                errors.append(f"{label}: direction{where} must be {a}, {b} or both, not {h['direction']!r}")
        if r.get("nesting") and r.get("distance") not in (None, "nesting"):
            errors.append(f"{label}: nesting is true but distance is {r['distance']!r}")
        _check_bond(errors, label, r, rtypes)

    ended = {p["id"] for p in people if p.get("status") == "ended"}
    for r in rels:
        if r.get("status", "active") == "active":
            for p in r["parties"]:
                if p["person"] in ended:
                    errors.append(f"relationship {r['id']}: is active but {p['person']} is marked ended")
    return errors


# ---------------------------------------------------------------- derived views

def snapshot(doc: Doc, date: str | None = None) -> list[Doc]:
    """Relationships active on `date` (YYYY[-MM[-DD]]), or currently active when date is None."""
    return [r for r in doc["relationships"] if status_at(r, date) == "active"]


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


def bonded_groups(doc: Doc) -> list[Doc]:
    """Groups that relate as one unit (they carry relationship types)."""
    return [g for g in doc.get("groups", []) if g.get("types")]


def stats(doc: Doc) -> dict[str, Any]:
    doc = upgrade(doc)
    active = snapshot(doc)
    open_rels = [r for r in doc["relationships"] if not is_obscured(doc, r)]
    degree = Counter(p["person"] for r in active for p in r["parties"])
    return {
        "people": len(doc["people"]),
        "groups": len(doc.get("groups", [])),
        "group_bonds": len(bonded_groups(doc)),
        "relationships": len(doc["relationships"]),
        "active_relationships": len(active),
        "metamour_pairs": len(metamours(doc, active)),
        "obscured_relationships": sum(is_obscured(doc, r) for r in doc["relationships"]),
        # Obscured relationships never count towards type or distance figures (spec §8).
        "types": dict(Counter(t for r in open_rels for t in r["types"])),
        "distance": dict(Counter(distance_of(r) or "unspecified" for r in open_rels)),
        "most_connected": degree.most_common(3),
    }
