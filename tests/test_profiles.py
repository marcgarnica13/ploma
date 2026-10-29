"""Tests for venue profiles, discipline cards and the profile loader (scripts/profiles.py)."""
from __future__ import annotations

import pytest

import _yamlio
import _yamlmini
import profiles
from _banned import BANNED_RE, EM_DASH_RE
from _findings import FAIL

SHIPPED = ["springer-ml", "llncs-conference", "ieee-conference", "acm-sigconf", "elsevier", "arxiv",
           "generic-journal", "generic-conference"]
DISCIPLINES = ["ml", "generic", "social-science"]


def _fails(findings):
    return [f for f in findings if f.status == FAIL]


@pytest.mark.parametrize("key", SHIPPED)
def test_shipped_venue_validates(key):
    venue = profiles.load_venue(key, None)
    assert _fails(profiles.validate_venue(venue)) == []
    assert venue["key"] == key
    assert list(venue) == list(profiles.VENUE_KEYS)


@pytest.mark.parametrize("key", DISCIPLINES)
def test_shipped_discipline_validates(key):
    card = profiles.load_discipline(key, None)
    assert _fails(profiles.validate_discipline(card)) == [] and card["key"] == key


def test_pool_sums_to_one():
    for key in SHIPPED:
        pool = profiles.load_venue(key, None)["referee_pool"]
        assert set(pool) == set(profiles.POOL_KEYS)
        assert abs(sum(pool.values()) - 1.0) <= 0.001, key


def test_pool_bad_sum_and_unknown_key_fail():
    venue = profiles.load_venue("springer-ml", None)
    venue["referee_pool"] = dict(venue["referee_pool"], CLARITY=0.5)
    assert any("referee_pool" in f.id for f in _fails(profiles.validate_venue(venue)))
    venue = profiles.load_venue("springer-ml", None)
    venue["referee_pool"]["TASTE"] = 0.0
    assert any("TASTE" in f.summary for f in _fails(profiles.validate_venue(venue)))


def test_shape_problems_fail():
    venue = profiles.load_venue("arxiv", None)
    venue["doc_classes"] = ["article", 3]
    venue["methods_adjustments"] = {"evaluation": [30, "35"]}
    del venue["bar"]
    venue["extra"] = 1
    findings = profiles.validate_venue(venue)
    ids = {f.id for f in _fails(findings)}
    assert {"venue.doc_classes", "venue.methods_adjustments.evaluation", "venue.bar"} <= ids
    assert [f.status for f in findings if f.id == "venue.extra"] == ["WARN"]
    assert _fails(profiles.validate_venue("not a dict"))


def test_discipline_shape_problems_fail():
    card = profiles.load_discipline("ml", None)
    card["paper_types"][0]["weights"]["x"] = "high"
    card["default_paper_type"] = "nope"
    ids = {f.id for f in _fails(profiles.validate_discipline(card))}
    assert "discipline.default_paper_type" in ids and any(i.startswith("discipline.paper_types") for i in ids)


def test_page_budget_and_anonymity():
    budgets = {k: profiles.load_venue(k, None)["page_budget"] for k in SHIPPED}
    assert budgets == {k: None for k in SHIPPED} | {"llncs-conference": 12, "ieee-conference": 8,
                                                     "acm-sigconf": 10}
    anon = {k for k in SHIPPED if profiles.load_venue(k, None)["anonymized"]}
    assert anon == {"llncs-conference", "ieee-conference", "acm-sigconf"}
    assert "arxiv_rules" in profiles.load_venue("arxiv", None)["submission_checks"]


def test_shadowing(tmp_path, repo_root):
    (tmp_path / "ploma.d/venues").mkdir(parents=True)
    text = (repo_root / "venues/springer-ml.yaml").read_text(encoding="utf-8")
    assert "page_budget: null" in text
    (tmp_path / "ploma.d/venues/springer-ml.yaml").write_text(text.replace("page_budget: null", "page_budget: 20"))
    assert profiles.load_venue("springer-ml", tmp_path)["page_budget"] == 20
    assert profiles.load_venue("springer-ml", None)["page_budget"] is None


def test_project_only_venue_listed(tmp_path, repo_root):
    (tmp_path / "ploma.d/venues").mkdir(parents=True)
    text = (repo_root / "venues/generic-journal.yaml").read_text(encoding="utf-8")
    (tmp_path / "ploma.d/venues/my-venue.yaml").write_text(text.replace("key: generic-journal", "key: my-venue"))
    keys = profiles.list_venues(tmp_path)
    assert "my-venue" in keys and keys == sorted(keys) and set(SHIPPED) <= set(keys)
    assert profiles.list_venues(None) == sorted(SHIPPED)
    assert profiles.load_venue("my-venue", tmp_path)["key"] == "my-venue"


def test_unknown_key_lists_available():
    with pytest.raises(profiles.ProfileError, match="generic-journal"):
        profiles.load_venue("nope", None)
    with pytest.raises(profiles.ProfileError, match="generic"):
        profiles.load_discipline("nope", None)


def test_malformed_file_raises_profile_error(tmp_path):
    (tmp_path / "ploma.d/venues").mkdir(parents=True)
    (tmp_path / "ploma.d/venues/bad.yaml").write_text("- just\n- a list\n")
    with pytest.raises(profiles.ProfileError, match="bad.yaml"):
        profiles.load_venue("bad", tmp_path)


def test_path_like_key_rejected():
    with pytest.raises(profiles.ProfileError):
        profiles.load_venue("../ploma", None)


def test_venues_for_class():
    llncs = profiles.venues_for_class("llncs", None)
    assert "llncs-conference" in llncs and "springer-ml" in llncs
    assert llncs[0] == "llncs-conference"
    assert profiles.venues_for_class("article", None)[0] == "generic-journal"
    assert profiles.venues_for_class("article", None).index("generic-journal") < \
        profiles.venues_for_class("article", None).index("arxiv")
    assert profiles.venues_for_class("IEEEtran", None) == ["ieee-conference", "generic-conference"]
    assert profiles.venues_for_class("elsarticle", None) == ["elsevier", "generic-journal"]
    assert profiles.venues_for_class("unknownclass", None) == []
    assert profiles.venues_for_class(None, None) == []


def test_all_shipped_yaml_loads_without_pyyaml(repo_root):
    for p in sorted((repo_root / "venues").glob("*.yaml")) + sorted((repo_root / "disciplines").glob("*.yaml")):
        assert _yamlmini.load(p.read_text(encoding="utf-8")) == _yamlio.load_yaml(p), p


def test_no_domain_words_in_generic_files(repo_root):
    for p in list((repo_root / "venues").glob("*.yaml")) + [repo_root / "disciplines/generic.yaml"]:
        assert not BANNED_RE.search(p.read_text(encoding="utf-8")), p


def test_no_em_dashes_in_profiles(repo_root):
    for p in list((repo_root / "venues").glob("*.yaml")) + list((repo_root / "disciplines").glob("*.yaml")):
        assert not EM_DASH_RE.search(p.read_text(encoding="utf-8")), p


def test_cli_list_and_validate(capsys):
    assert profiles.main(["list"]) == 0
    assert "springer-ml" in capsys.readouterr().out
    assert profiles.main(["--json", "validate"]) == 0
    assert profiles.main(["show", "nope"]) == 2


def test_schemas_match_loader_keys(repo_root):
    import json
    venue = json.loads((repo_root / "schemas/venue.schema.json").read_text(encoding="utf-8"))
    disc = json.loads((repo_root / "schemas/discipline.schema.json").read_text(encoding="utf-8"))
    assert tuple(venue["required"]) == profiles.VENUE_KEYS == tuple(venue["properties"])
    assert set(venue["properties"]["referee_pool"]["required"]) == set(profiles.POOL_KEYS)
    assert tuple(disc["required"]) == profiles.DISCIPLINE_KEYS


def test_inventory_offers_project_venue(tmp_path, repo_root):
    import inventory
    (tmp_path / "paper.tex").write_text("\\documentclass{IEEEtran}\n\\begin{document}\nx\n\\end{document}\n")
    (tmp_path / "ploma.d/venues").mkdir(parents=True)
    text = (repo_root / "venues/ieee-conference.yaml").read_text(encoding="utf-8")
    (tmp_path / "ploma.d/venues/my-ieee.yaml").write_text(text.replace("key: ieee-conference", "key: my-ieee"))
    inv = inventory.inventory(tmp_path)
    opts = {g["key"]: g for g in inventory.gaps(inv, inventory.propose_config(inv))}["venue.profile"]["options"]
    assert opts == ["ieee-conference", "my-ieee", "generic-conference", "generic-journal"]
    assert profiles.venues_for_class("IEEEtran", tmp_path) == ["ieee-conference", "my-ieee", "generic-conference"]


def test_llncs_re_spares_venue_key():
    from _banned import LLNCS_RE
    assert LLNCS_RE.search("documentclass{llncs}") and LLNCS_RE.search("LLNCS")
    assert not LLNCS_RE.search("venue: llncs-conference")
