import copy
import json
from pathlib import Path

import pytest

from polyml import metamours, snapshot, stats, validate
from polyml.cli import main

SAMPLE = Path(__file__).resolve().parents[2] / "spec" / "examples" / "sample.polyml.json"


@pytest.fixture
def doc():
    return json.loads(SAMPLE.read_text("utf-8"))


def test_sample_is_valid(doc):
    assert validate(doc) == []


@pytest.mark.parametrize("mutate, expected", [
    (lambda d: d["people"].append(dict(d["people"][0])), "duplicate person id"),
    (lambda d: d["relationships"][0]["parties"][1].update(person="nobody"), "unknown person"),
    (lambda d: d["relationships"][0]["types"].append("made-up"), "unknown type"),
    (lambda d: d["relationships"][2]["dynamics"].append("nope"), "unknown dynamic"),
    (lambda d: d["groups"][0].update(parent="maple-house"), "cycle"),
    (lambda d: d["relationships"][1]["parties"].reverse() or d["relationships"].append(
        {**copy.deepcopy(d["relationships"][1]), "id": "dup"}), "same pair"),
    (lambda d: d["relationships"][0].update(status="ended"), "does not match"),
    (lambda d: d["relationships"][0]["history"].reverse(), "overlap"),
    (lambda d: d.update(polyml="9"), "was expected"),
])
def test_invalid(doc, mutate, expected):
    mutate(doc)
    assert any(expected in e for e in validate(doc)), validate(doc)


def test_snapshot_by_date(doc):
    ids = lambda rs: {r["id"] for r in rs}
    assert "ash-bea" not in ids(snapshot(doc, "2021-05"))  # paused
    assert "cal-fox" in ids(snapshot(doc, "2019"))
    assert "cal-fox" not in ids(snapshot(doc))
    assert "bea-dee" not in ids(snapshot(doc, "2022-01"))


def test_metamours(doc):
    m = metamours(doc)
    assert frozenset({"ash", "dee"}) in m  # share bea
    assert frozenset({"ash", "bea"}) not in m


def test_stats(doc):
    s = stats(doc)
    assert s["people"] == 6 and s["active_relationships"] == 4


def test_cli(tmp_path, capsys):
    assert main(["validate", str(SAMPLE)]) == 0
    assert main(["stats", str(SAMPLE)]) == 0
    assert '"people": 6' in capsys.readouterr().out
