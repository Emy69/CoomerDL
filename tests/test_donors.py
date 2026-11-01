"""
Parsing the donor list.

The list moved to https://github.com/Emy69/Proyect-C and changed shape on the
way: it used to be a list of objects and is now an object whose "donantes"
key holds plain names.
"""
import pytest

from app.donors import DONORS_URL, DonorsWorker

parse = DonorsWorker._parse_donors

# A trimmed copy of the published file, kept as a fixture so the suite never
# depends on the network or on who donated this month.
PUBLISHED = {
    "actualizado": "2026-09-14",
    "total": 3,
    "donantes": ["YoungTae Kim", "carl massey", "MrHano"],
}


def test_the_published_shape_is_parsed():
    donors = parse(PUBLISHED)

    assert [d["name"] for d in donors] == PUBLISHED["donantes"]
    assert len(donors) == PUBLISHED["total"]


def test_the_grid_can_read_every_entry():
    """The modal calls .get("name") on each donor, so all must be dicts."""
    assert all(isinstance(d, dict) and d.get("name") for d in parse(PUBLISHED))


def test_the_published_order_is_preserved():
    """There are no amounts any more, so the file's own order is what shows."""
    def to_float(value):
        try:
            return float(value)
        except Exception:
            return 0.0

    donors = parse(PUBLISHED)
    donors.sort(key=lambda d: to_float(d.get("donated_amount", 0)), reverse=True)

    assert [d["name"] for d in donors] == PUBLISHED["donantes"]


def test_the_previous_list_of_objects_still_parses():
    """A rollback of the source should not blank the modal."""
    old = [{"name": "Alice", "donated_amount": "20"}, {"name": "Bob", "donated_amount": "5"}]

    assert parse(old) == old


@pytest.mark.parametrize("payload", [None, {}, [], "nope", 42, {"donantes": None}])
def test_malformed_payloads_degrade_to_an_empty_list(payload):
    assert parse(payload) == []


def test_unusable_entries_are_dropped_rather_than_breaking_the_modal():
    payload = {"donantes": ["", "   ", "Real", 7, None, {"name": "Dict"}]}

    assert parse(payload) == [{"name": "Real"}, {"name": "Dict"}]


def test_the_retired_endpoint_is_gone():
    import app.donors as donors_module
    import inspect

    source = inspect.getsource(donors_module)

    assert "emydevs.com" not in source
    assert DONORS_URL.startswith("https://raw.githubusercontent.com/Emy69/Proyect-C/")
