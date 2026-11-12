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

NAMES = [
    "Alex Example", "Sam Sample", "Morgan Test", "Jamie Fiction", "Taylor Demo", "Robin Placeholder",
    "Casey Dummy", "Drew Prototype", "Elliot Mock", "Finley Trial", "Greer Specimen", "Harper Instance",
    "Indigo Template", "Jordan Model", "Kai Pattern", "Lane Prototype", "Marlow Illustration", "Nolan Sample",
    "Owen Exemplar", "Parker Representation", "Quinn Demonstration", "Riley Embodiment", "Sawyer Manifestation",
    "Tatum Personification", "Ulysses Typification", "Vesper Instantiation", "Wren Realization", "Xander Actualization"
]

STREETS = [
    "Example Street", "Sample Road", "Test Avenue", "Fiction Lane", "Demo Close",
    "Placeholder Way", "Prototype Drive", "Mock Boulevard", "Trial Terrace", "Specimen Court",
    "Template Circle", "Model Mews", "Pattern Plaza", "Illustration Rise", "Exemplar Grove",
    "Representation Row", "Demonstration Dale", "Embodiment End", "Manifestation Mount",
    "Personification Park", "Typification Trace", "Instantiation Inlet", "Realization Ridge",
    "Actualization Alley"
]

ISSUES = [
    "a dripping tap", "a cold radiator", "a sticking window", "a loose cupboard hinge",
    "a blocked sink", "a faulty hallway light", "a noisy boiler", "a broken door handle",
    "a leaking pipe", "a tripping circuit breaker", "a cracked tile", "a mouldy ceiling patch",
    "a faulty extractor fan", "a jammed door", "a broken toilet flush", "a smelly drain",
    "a loose floorboard", "a cracked window pane", "a broken light switch", "a dripping shower",
    "a blocked gutter", "a faulty immersion heater", "a broken curtain rail", "a loose banister",
    "a cracked bath panel", "a leaking overflow", "a faulty thermostat", "a broken cupboard door",
    "a sticking drawer", "a loose kitchen unit", "a cracked worktop", "a leaking washing machine"
]

BOOKINGS = [
    "a dental check-up", "a haircut", "an eye test", "a consultation", "a service appointment",
    "a viewing", "a massage", "a physiotherapy session", "a podiatry appointment", "a hearing test",
    "a blood test", "a vaccination", "a medication review", "a chiropody appointment", "an osteopathy session",
    "a counselling session", "a dietitian appointment", "a speech therapy session", "an occupational therapy appointment",
    "a wheelchair assessment"
]

TIMES = [
    "Monday morning", "Tuesday afternoon", "Wednesday morning", "Thursday afternoon", "Friday morning",
    "Monday afternoon", "Tuesday morning", "Wednesday afternoon", "Thursday morning", "Friday afternoon",
    "early Monday", "late Tuesday", "mid-week Wednesday", "Thursday lunchtime", "Friday early",
    "first thing Monday", "end of day Tuesday", "Wednesday mid-morning", "Thursday late afternoon", "Friday midday"
]

OPENERS = [
    "Hello, this is a test call",
    "Good morning, I am calling with an invented scenario",
    "Hi, this is a fictional service request",
    "Good afternoon, I'm calling about a made-up issue",
    "Hello, this is a simulated call for testing",
    "Hi there, I have a pretend enquiry",
    "Good morning, this is a test scenario",
    "Hello, I'm calling with a fabricated request",
    "Hi, this is a dummy call for QA purposes",
    "Good afternoon, I have an imaginary issue to report"
]

CLOSERS = [
    "Thank you, that is clear",
    "Understood, I will follow that advice",
    "Thanks, I have noted the next step",
    "Right, I understand what to do",
    "Okay, that makes sense, thank you",
    "Great, I'll do that, thanks",
    "Perfect, thanks for your help",
    "Understood, thanks for clarifying",
    "Okay, I know what to do now",
    "Thanks, that's very helpful"
]

AGENT_OPENERS = [
    "How can I help with this fictional scenario?",
    "What can I do for you in this test call?",
    "How may I assist with this invented situation?",
    "What's the simulated issue today?",
    "How can I help with this made-up request?",
    "What's the pretend problem you're reporting?",
    "How can I assist with this test scenario?",
    "What's the fabricated issue?",
    "How can I help with this dummy call?",
    "What imaginary issue can I help with?"
]

AGENT_RESPONSES_REPAIR = [
    "I have recorded the fictional repair request for {name} on {number}",
    "I've logged the made-up repair for {name} at {number}",
    "The pretend repair request is noted for {name} on {number}",
    "I've recorded the simulated repair for {name} at {number}",
    "The test repair is logged for {name} on {number}",
    "I've noted the dummy repair for {name} at {number}",
    "The fabricated repair request is saved for {name} on {number}",
    "I've logged the imaginary repair for {name} at {number}",
    "The QA repair is recorded for {name} on {number}",
    "I've saved the prototype repair for {name} at {number}"
]

AGENT_RESPONSES_LANDLORD = [
    "I have recorded the fictional landlord enquiry for {name} on {number}",
    "I've logged the made-up landlord query for {name} at {number}",
    "The pretend landlord enquiry is noted for {name} on {number}",
    "I've recorded the simulated landlord query for {name} at {number}",
    "The test landlord enquiry is logged for {name} on {number}",
    "I've noted the dummy landlord query for {name} at {number}",
    "The fabricated landlord enquiry is saved for {name} on {number}",
    "I've logged the imaginary landlord query for {name} at {number}",
    "The QA landlord enquiry is recorded for {name} on {number}",
    "I've saved the prototype landlord query for {name} at {number}"
]

AGENT_RESPONSES_BOOKING = [
    "I can record that fictional request under {name}; your test contact is {number}",
    "I'll log that made-up booking for {name} at {number}",
    "The pretend appointment is noted for {name} on {number}",
    "I've recorded the simulated booking for {name} at {number}",
    "The test appointment is logged for {name} on {number}",
    "I've noted the dummy booking for {name} at {number}",
    "The fabricated appointment is saved for {name} on {number}",
    "I've logged the imaginary booking for {name} at {number}",
    "The QA appointment is recorded for {name} on {number}",
    "I've saved the prototype booking for {name} at {number}"
]

HAZARD_REPORT_VARIANTS = {
    "gas": [
        "I can smell gas near the boiler",
        "There's a strong smell of gas by the boiler",
        "I'm reporting a gas smell near the boiler",
        "Gas smell detected near the boiler",
        "I think there's a gas leak by the boiler",
        "Strong gas odour coming from the boiler area",
        "I can smell gas in the kitchen near the boiler",
        "There's a gas smell around the boiler cupboard",
        "Reporting a gas smell near the heating system",
        "Gas odour detected by the boiler"
    ],
    "lift": [
        "I am trapped inside the lift",
        "I'm stuck in the lift",
        "The lift has stopped and I'm trapped inside",
        "I'm trapped in the elevator",
        "The lift broke down and I'm inside",
        "I'm stuck between floors in the lift",
        "Lift entrapment - I'm inside and it won't move",
        "I'm trapped in the lift shaft",
        "The lift stopped working with me inside",
        "I'm stuck in the lift and can't get out"
    ],
    "fire": [
        "There is smoke and a fire in the hallway",
        "There's a fire in the hallway with smoke",
        "I can see flames and smoke in the hallway",
        "Fire in the hallway, smoke everywhere",
        "There's a fire burning in the corridor",
        "Smoke and flames in the hallway",
        "The hallway is on fire",
        "Fire outbreak in the hallway",
        "I'm reporting a fire in the hallway",
        "There's smoke and fire in the communal hallway"
    ],
    "co": [
        "The carbon monoxide alarm is sounding",
        "The CO alarm is going off",
        "Carbon monoxide detector is beeping",
        "The carbon monoxide alarm has activated",
        "CO alarm sounding in the property",
        "Carbon monoxide alarm triggered",
        "The CO detector is alarming",
        "Carbon monoxide alarm is sounding loudly",
        "The CO monitor is going off",
        "Carbon monoxide alarm activation"
    ],
    "flood_with_electrics": [
        "Water is reaching the electrical sockets",
        "Water has reached the electrical sockets",
        "Flood water is touching the electric sockets",
        "Water is up to the electrical outlets",
        "The flood water has reached the power points",
        "Water is contacting the electrical sockets",
        "Electrical sockets are getting wet from the flood",
        "Flood water reaching the wall sockets",
        "Water has risen to the electrical outlets",
        "The flooding has reached the electrical sockets"
    ]
}

HAZARD_RESPONSE_VARIANTS = {
    "gas": [
        "Please leave the building now and call 0800 111 999 from outside",
        "You must leave the building immediately and call 0800 111 999 from outside",
        "Evacuate the building now and call 0800 111 999 from a safe location",
        "Leave the property right now and call 0800 111 999 from outside",
        "Get out of the building and call 0800 111 999 from outdoors",
        "You need to exit the building and call 0800 111 999 from outside",
        "Evacuate immediately and call 0800 111 999 from outside the building",
        "Leave the premises now and call 0800 111 999 from a safe place",
        "Get out and call 0800 111 999 from outside",
        "You must evacuate and call 0800 111 999 from outside"
    ],
    "lift": [
        "Call 999 now and do not try to force the doors",
        "Call 999 immediately and don't try to open the doors",
        "Phone 999 right now and do not attempt to force the lift doors",
        "Call 999 now, do not try to pry the doors open",
        "Dial 999 immediately and don't force the doors",
        "Call 999 now and stay away from the doors",
        "Phone 999 and do not attempt to exit the lift yourself",
        "Call 999 immediately, don't try to force the doors open",
        "Ring 999 now and do not touch the doors",
        "Call 999 and wait for help, don't force the doors"
    ],
    "fire": [
        "Leave the building and call 999 now",
        "Evacuate the building and call 999 immediately",
        "Get out of the building and call 999 now",
        "Leave the premises and call 999 right now",
        "You must leave the building and call 999",
        "Evacuate now and call 999",
        "Leave the building immediately and call 999",
        "Get out and call 999 now",
        "You need to leave and call 999",
        "Exit the building and call 999 immediately"
    ],
    "co": [
        "Leave the building and call 999 now",
        "Evacuate the building and call 999 immediately",
        "Get out of the building and call 999 now",
        "Leave the premises and call 999 right now",
        "You must leave the building and call 999",
        "Evacuate now and call 999",
        "Leave the building immediately and call 999",
        "Get out and call 999 now",
        "You need to leave and call 999",
        "Exit the building and call 999 immediately"
    ],
    "flood_with_electrics": [
        "Keep away from the water and call 999 now",
        "Stay away from the water and call 999 immediately",
        "Do not go near the water and call 999 now",
        "Keep clear of the water and call 999 right now",
        "Stay away from the flooded area and call 999",
        "Do not touch the water and call 999 now",
        "Keep back from the water and call 999",
        "Stay clear of the water and call 999 immediately",
        "Do not approach the water and call 999",
        "Keep away from the flood water and call 999 now"
    ]
}


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
    
    # Hazard distribution: 500 per hazard class (2500 total), rest "none"
    # Spread across MaintenanceOS and LandlordOS only (not ReceptionistOS)
    hazard = "none"
    if market != "ReceptionistOS":
        hazard_index = index // 20  # 2500 scripts per hazard across both markets
        if hazard_index < 500:
            hazard = HAZARDS[1 + hazard_index % 5]
    
    name = rng.choice(NAMES)
    number = f"07700 900{index % 1000:03d}"
    address = f"Flat {1 + index % 80}, {1 + (index * 7) % 200} {rng.choice(STREETS)}, Testford, TE{index % 10} {index % 10}ZZ"
    
    opener = rng.choice(OPENERS)
    closer = rng.choice(CLOSERS)
    agent_opener = rng.choice(AGENT_OPENERS)
    
    if hazard != "none":
        report = rng.choice(HAZARD_REPORT_VARIANTS[hazard])
        response = rng.choice(HAZARD_RESPONSE_VARIANTS[hazard])
        topic = f"{report} at {address}"
        escalation = HAZARD_DETAILS[hazard][3]
        intent = HAZARD_DETAILS[hazard][2]
    elif market == "ReceptionistOS":
        booking = rng.choice(BOOKINGS)
        time = rng.choice(TIMES)
        topic = f"I would like {booking} for {time}"
        response = rng.choice(AGENT_RESPONSES_BOOKING).format(name=name, number=number)
        intent, escalation = "booking", "none"
    else:
        issue = rng.choice(ISSUES)
        topic = f"I need to report {issue} at {address}"
        if market == "LandlordOS":
            response = rng.choice(AGENT_RESPONSES_LANDLORD).format(name=name, number=number)
            intent = "landlord_enquiry"
        else:
            response = rng.choice(AGENT_RESPONSES_REPAIR).format(name=name, number=number)
            intent = "repair"
        escalation = "none"
    
    # Vary the turn structure slightly
    turn_structure = rng.randint(0, 2)
    turns = []
    turns.append({"speaker": "caller", "text": f"{opener}. My name is {name}.", "escalation_label": "none", "intent_label": intent})
    turns.append({"speaker": "agent", "text": agent_opener, "escalation_label": "none", "intent_label": intent})
    turns.append({"speaker": "caller", "text": topic, "escalation_label": escalation, "intent_label": intent})
    turns.append({"speaker": "agent", "text": response, "escalation_label": escalation, "intent_label": intent})
    turns.append({"speaker": "caller", "text": closer, "escalation_label": escalation, "intent_label": intent})
    
    # Add optional extra turn for variety
    if turn_structure >= 1:
        extra_caller = rng.choice([
            "Is there anything else I should do?",
            "Should I wait here for someone?",
            "Do you need any more details?",
            "Will someone contact me?",
            "Is that everything?",
            "What happens next?",
            "Should I stay on the line?",
            "Do I need to do anything else?",
            "Will I get a reference number?",
            "Is there a reference for this?"
        ])
        extra_agent = rng.choice([
            "No, that's all we need for now",
            "We'll contact you if needed",
            "You'll get a reference by text",
            "Someone will be in touch shortly",
            "That's everything, thank you",
            "We have all the details we need",
            "A reference will be sent to you",
            "No further action needed from you",
            "You'll receive confirmation soon",
            "That's all for now"
        ])
        turns.append({"speaker": "caller", "text": extra_caller, "escalation_label": escalation, "intent_label": intent})
        turns.append({"speaker": "agent", "text": extra_agent, "escalation_label": escalation, "intent_label": intent})
    
    if turn_structure == 2:
        final_caller = rng.choice([
            "Okay, thanks again",
            "Right, thank you",
            "Thanks, bye",
            "Okay, goodbye",
            "Thanks, that's great",
            "Perfect, thanks",
            "Great, thank you",
            "Okay, cheers",
            "Thanks very much",
            "Right, thanks"
        ])
        turns.append({"speaker": "caller", "text": final_caller, "escalation_label": escalation, "intent_label": intent})
    
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