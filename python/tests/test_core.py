import copy
import json
from pathlib import Path

import pytest

from polyml import (bonded_groups, distance_of, is_anarchic, members_at, metamours, snapshot, stats, status_at,
                    types_at, validate)
from polyml.cli import main

SAMPLE = Path(__file__).resolve().parents[2] / "spec" / "examples" / "sample.polyml.json"


@pytest.fixture
def doc():
    return json.loads(SAMPLE.read_text("utf-8"))


def rel(doc, rid):
    return next(r for r in doc["relationships"] if r["id"] == rid)


def group(doc, gid):
    return next(g for g in doc["groups"] if g["id"] == gid)


def test_sample_is_valid(doc):
    assert validate(doc) == []


def test_v01_document_still_valid(doc):
    v01 = {"polyml": "0.1", "people": [{"id": "a", "name": "A"}, {"id": "b", "name": "B"}],
           "relationships": [{"id": "ab", "parties": [{"person": "a"}, {"person": "b"}], "types": ["romantic"],
                              "nesting": True}]}
    assert validate(v01) == []
    assert distance_of(v01["relationships"][0]) == "nesting"


@pytest.mark.parametrize("mutate, expected", [
    (lambda d: d["people"].append(dict(d["people"][0])), "duplicate person id"),
    (lambda d: rel(d, "ash-bea")["parties"][1].update(person="nobody"), "unknown person"),
    (lambda d: rel(d, "ash-bea")["types"].append("made-up"), "unknown type"),
    (lambda d: rel(d, "bea-dee")["dynamics"].append("nope"), "unknown dynamic"),
    (lambda d: rel(d, "cal-fox")["history"][0]["types"].append("nope"), "in history"),
    (lambda d: group(d, "lantern").update(parent="maple-house"), "cycle"),
    (lambda d: d["relationships"].append({**copy.deepcopy(rel(d, "ash-cal")), "id": "dup"}), "same pair"),
    (lambda d: rel(d, "ash-bea").update(status="ended"), "does not match"),
    (lambda d: rel(d, "ash-bea")["history"].reverse(), "overlap"),
    (lambda d: rel(d, "ash-bea").update(since="2019-01"), "differs from the first history period"),
    (lambda d: d.update(polyml="9"), "is not one of"),
    # relationship anarchy
    (lambda d: rel(d, "dee-eli").update(priority="primary"), "not used under relationship anarchy"),
    (lambda d: rel(d, "ash-cal").update(types=[]), "needs at least one type"),
    # distance, membership, groups as units, vocab, person status
    (lambda d: rel(d, "ash-cal").update(nesting=True), "nesting is true"),
    (lambda d: group(d, "maple-house")["members"].append({"person": "dee", "from": "2024", "to": "2023"}),
     "ends before it starts"),
    (lambda d: group(d, "spark")["members"].append("bea"), "more than once"),
    (lambda d: group(d, "spark")["types"].append("nope"), "group spark: unknown type"),
    (lambda d: d["vocab"]["relationship_types"].append({"id": "romantic"}), "repeats a core term"),
    (lambda d: d["people"][0].update(status="ended"), "is marked ended"),
    (lambda d: rel(d, "ash-bea").update(closeness=9), "greater than the maximum"),
])
def test_invalid(doc, mutate, expected):
    mutate(doc)
    errs = validate(doc)
    assert any(expected in e for e in errs), errs


def test_snapshot_by_date(doc):
    ids = lambda rs: {r["id"] for r in rs}
    assert "ash-bea" not in ids(snapshot(doc, "2021-05"))  # paused
    assert "cal-fox" in ids(snapshot(doc, "2019"))
    assert "bea-dee" not in ids(snapshot(doc, "2022-01"))
    assert status_at(rel(doc, "bea-eli"), "2023") is None


def test_types_change_over_time(doc):
    assert types_at(rel(doc, "cal-fox"), "2019") == ["sexual"]
    assert types_at(rel(doc, "cal-fox"), "2021") == ["friend"]
    assert types_at(rel(doc, "cal-fox")) == ["friend"]
    assert types_at(rel(doc, "bea-dee"), "2022-06") == ["friend"]


def test_dated_membership(doc):
    house = group(doc, "maple-house")
    assert "cal" in members_at(house, "2021")
    assert "cal" not in members_at(house, "2024")
    assert "cal" not in members_at(house)
    assert members_at(group(doc, "lantern")) == ["ash", "bea", "cal", "dee", "eli"]


def test_relationship_anarchy(doc):
    assert is_anarchic(doc, rel(doc, "dee-eli"))
    assert not is_anarchic(doc, rel(doc, "ash-bea"))


def test_groups_as_units(doc):
    assert [g["id"] for g in bonded_groups(doc)] == ["spark"]


def test_metamours(doc):
    m = metamours(doc)
    assert frozenset({"ash", "dee"}) in m  # share bea
    assert frozenset({"ash", "bea"}) not in m


def test_stats(doc):
    s = stats(doc)
    assert s["people"] == 6 and s["active_relationships"] == 6 and s["group_bonds"] == 1
    assert s["distance"]["long-distance"] == 3


def test_cli(capsys):
    assert main(["validate", str(SAMPLE)]) == 0
    assert main(["stats", str(SAMPLE)]) == 0
    assert '"people": 6' in capsys.readouterr().out
