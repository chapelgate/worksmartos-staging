import json
import re
from collections import Counter

from generator import CONDITIONS, HAZARDS, MARKET_COUNTS, make_script


def test_schema_and_labels():
    script = make_script(0, 20261112)
    assert set(script) == {"script_id", "market", "phone_line_condition", "hazard_class", "turns"}
    assert script["phone_line_condition"] in CONDITIONS
    assert script["hazard_class"] in HAZARDS
    assert len(script["turns"]) >= 5
    assert all(set(turn) == {"speaker", "text", "escalation_label", "intent_label"} for turn in script["turns"])


def test_market_counts_and_condition_balance():
    markets = Counter(make_script(i, 20261112)["market"] for i in range(50000))
    conditions = Counter(make_script(i, 20261112)["phone_line_condition"] for i in range(50000))
    assert markets == MARKET_COUNTS
    assert set(conditions.values()) == {5000}


def test_hazard_coverage_and_safe_labels():
    scripts = [make_script(i, 20261112) for i in range(50000)]
    hazards = Counter(script["hazard_class"] for script in scripts)
    assert all(hazards[name] >= 200 for name in HAZARDS[1:])
    for script in scripts:
        labels = {turn["escalation_label"] for turn in script["turns"]}
        if script["hazard_class"] == "gas":
            assert "leave_and_call_gas" in labels
        elif script["hazard_class"] in HAZARDS[2:]:
            assert "call_999_now" in labels


def test_unique_ids_and_texts():
    scripts = [make_script(i, 20261112) for i in range(50000)]
    ids = {script["script_id"] for script in scripts}
    texts = {" ".join(turn["text"] for turn in script["turns"]) for script in scripts}
    assert len(ids) == 50000
    assert len(texts) >= 49000


def test_only_fictional_phone_numbers_and_postcodes():
    for index in range(50000):
        text = json.dumps(make_script(index, 20261112))
        phones = re.findall(r"(?:0\d[\d ]{8,12})", text)
        assert all(phone.replace(" ", "").startswith(("07700900", "0800111999")) for phone in phones)
        if make_script(index, 20261112)["market"] != "ReceptionistOS":
            assert "Testford" in text


def test_deterministic():
    assert make_script(12345, 20261112) == make_script(12345, 20261112)
    assert make_script(12345, 20261112) != make_script(12345, 20261113)
