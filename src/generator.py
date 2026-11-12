import argparse
import gzip
import hashlib
import json
import random
import re
from pathlib import Path

MARKET_COUNTS = {"MaintenanceOS": 20000, "LandlordOS": 15000, "ReceptionistOS": 15000}
CONDITIONS = ["clean", "codec_loss", "packet_loss", "background_hiss", "street_noise", "room_noise", "reverberation", "low_volume", "cross_talk", "uk_regional_accent"]
HAZARDS = ["none", "gas", "lift", "fire", "co", "flood_with_electrics"]
HAZARD_DETAILS = {
    "gas": ("I can smell gas near the boiler", "Please leave the building now and call 0800 111 999 from outside", "gas_emergency", "leave_and_call_gas"),
    "lift": ("I am trapped inside the lift", "Call 999 now and do not try to force the doors", "lift_entrapment", "call_999_now"),
    "fire": ("There is smoke and a fire in the hallway", "Leave the building and call 999 now", "fire_emergency", "call_999_now"),
    "co": ("The carbon monoxide alarm is sounding", "Leave the building and call 999 now", "carbon_monoxide", "call_999_now"),
    "flood_with_electrics": ("Water is reaching the electrical sockets", "Keep away from the water and call 999 now", "flood_electrics", "call_999_now"),
}
NAMES = ["Alex Example", "Sam Sample", "Morgan Test", "Jamie Fiction", "Taylor Demo", "Robin Placeholder"]
STREETS = ["Example Street", "Sample Road", "Test Avenue", "Fiction Lane", "Demo Close"]
ISSUES = ["a dripping tap", "a cold radiator", "a sticking window", "a loose cupboard hinge", "a blocked sink", "a faulty hallway light"]
BOOKINGS = ["a dental check-up", "a haircut", "an eye test", "a consultation", "a service appointment", "a viewing"]
TIMES = ["Monday morning", "Tuesday afternoon", "Wednesday morning", "Thursday afternoon", "Friday morning"]


def allocation(index):
    if index < 20000:
        return "MaintenanceOS", index
    if index < 35000:
        return "LandlordOS", index - 20000
    return "ReceptionistOS", index - 35000


def make_script(index, seed):
    market, local = allocation(index)
    rng = random.Random(seed + index * 1000003)
    script_id = f"L4-{index + 1:05d}"
    condition = CONDITIONS[index % len(CONDITIONS)]
    hazard = HAZARDS[1 + (index // 10) % 5] if market != "ReceptionistOS" and local < 1250 else "none"
    name = rng.choice(NAMES)
    number = f"07700 900{index % 1000:03d}"
    address = f"Flat {1 + index % 80}, {1 + (index * 7) % 200} {rng.choice(STREETS)}, Testford, TE{index % 10} {index % 10}ZZ"
    if hazard != "none":
        report, response, intent, escalation = HAZARD_DETAILS[hazard]
        topic = f"{report} at {address}"
    elif market == "ReceptionistOS":
        topic = f"I would like {rng.choice(BOOKINGS)} for {rng.choice(TIMES)}"
        response = f"I can record that fictional request under {name}; your test contact is {number}"
        intent, escalation = "booking", "none"
    else:
        topic = f"I need to report {rng.choice(ISSUES)} at {address}"
        response = f"I have recorded the fictional repair request for {name} on {number}"
        intent, escalation = ("landlord_enquiry" if market == "LandlordOS" else "repair"), "none"
    openers = ["Hello, this is a test call", "Good morning, I am calling with an invented scenario", "Hi, this is a fictional service request"]
    closers = ["Thank you, that is clear", "Understood, I will follow that advice", "Thanks, I have noted the next step"]
    turns = [
        {"speaker": "caller", "text": f"{rng.choice(openers)}. My name is {name}.", "escalation_label": "none", "intent_label": intent},
        {"speaker": "agent", "text": "How can I help with this fictional scenario?", "escalation_label": "none", "intent_label": intent},
        {"speaker": "caller", "text": topic, "escalation_label": escalation, "intent_label": intent},
        {"speaker": "agent", "text": response, "escalation_label": escalation, "intent_label": intent},
        {"speaker": "caller", "text": rng.choice(closers), "escalation_label": escalation, "intent_label": intent},
    ]
    return {"script_id": script_id, "market": market, "phone_line_condition": condition, "hazard_class": hazard, "turns": turns}


def canonical_text(script):
    return " ".join(turn["text"] for turn in script["turns"])


def generate(output, start, count, seed):
    output.parent.mkdir(parents=True, exist_ok=True)
    opener = gzip.open if output.suffix == ".gz" else open
    with opener(output, "wt", encoding="utf-8") as handle:
        for index in range(start, start + count):
            handle.write(json.dumps(make_script(index, seed), separators=(",", ":")) + "\n")


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--count", type=int, required=True)
    parser.add_argument("--seed", type=int, default=20261112)
    args = parser.parse_args()
    if args.start < 0 or args.count < 1 or args.start + args.count > 50000:
        parser.error("range must be within the 50,000-script corpus")
    generate(args.output, args.start, args.count, args.seed)


if __name__ == "__main__":
    main()
