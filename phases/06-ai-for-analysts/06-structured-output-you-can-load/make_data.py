"""Build data/outputs.csv: synthetic complaint messages and SIMULATED model JSON for each one.

No model was called. Each message is made from known true fields (order id, issue,
refund wanted, amount, severity). The "model output" is those fields written as JSON,
then damaged in the ways real model JSON is damaged:

- wrappers around good JSON: a ```json code fence, a sentence before and after,
  a trailing comma, or an answer cut off part way (truncated)
- content problems inside JSON that parses: a number written as text, "yes" for a
  boolean, true for a number, a label outside the allowed list, a value out of range,
  a missing key, an extra key, a null where a value is required, a list instead of an
  object, NaN, an order id in the wrong format, an amount written as "Rs 250"

build(seed) also returns the defect behind every row, which the test uses as the
answer key. The csv holds only what a pipeline would really receive.

Run: python3 make_data.py
"""
import csv
import json
import os
import random

DEFAULT_SEED = 606
ISSUES = ["late", "missing_item", "wrong_item", "cold_food", "other"]
DISHES = ["paneer tikka", "dal makhani", "veg biryani", "chole", "thali", "misal pav", "poha"]

WRAPPERS = [("none", 0.55), ("fence", 0.20), ("prose", 0.08), ("trailing_comma", 0.12), ("truncated", 0.05)]
CONTENT = [("none", 0.62), ("string_number", 0.04), ("bool_string", 0.04), ("bool_for_int", 0.03),
           ("enum_off", 0.06), ("out_of_range", 0.04), ("missing_key", 0.04), ("extra_key", 0.05),
           ("null_required", 0.02), ("not_object", 0.02), ("nan_amount", 0.01), ("bad_order_id", 0.02),
           ("amount_text", 0.01)]
OFF_LABELS = ["Late delivery", "late ", "Cold food", "missing item", "LATE", "food quality"]


def pick(options, rng):
    r = rng.random()
    total = 0.0
    for name, chance in options:
        total += chance
        if r < total:
            return name
    return options[0][0]


def message_for(f, rng):
    """Write a customer message that carries the true fields."""
    dish = rng.choice(DISHES)
    what = {
        "late": "came %d minutes late" % rng.choice([35, 40, 50, 65, 80]),
        "missing_item": "arrived without the %s" % dish,
        "wrong_item": "had %s instead of what I ordered" % dish,
        "cold_food": "was cold, the %s especially" % dish,
        "other": "had a rude rider and a torn bag",
    }[f["issue"]]
    text = "Order %s %s." % (f["order_id"], what)
    if f["refund_requested"]:
        text += " Please refund Rs %d." % f["amount_rs"] if f["amount_rs"] is not None else " I want my money back."
    elif f["amount_rs"] is not None:
        text += " I paid Rs %d for it." % f["amount_rs"]
    if f["severity"] >= 4:
        text += " This is the third time."
    return text


def damage(fields, content, rng):
    """Return the JSON text for these fields with one content problem."""
    obj = dict(fields)
    if content == "string_number":
        obj["severity"] = str(obj["severity"])
    elif content == "bool_string":
        obj["refund_requested"] = "yes" if obj["refund_requested"] else "no"
    elif content == "bool_for_int":
        obj["severity"] = True
    elif content == "enum_off":
        obj["issue"] = rng.choice(OFF_LABELS)
    elif content == "out_of_range":
        if rng.random() < 0.5:
            obj["severity"] = rng.choice([0, 6, 7, 10])
        else:
            obj["amount_rs"] = rng.choice([-120, 25000, 99999])
    elif content == "missing_key":
        del obj[rng.choice(["amount_rs", "severity", "refund_requested"])]
    elif content == "extra_key":
        obj[rng.choice(["confidence", "notes", "customer_mood"])] = rng.choice([0.92, "angry", "check with kitchen"])
    elif content == "null_required":
        obj[rng.choice(["issue", "order_id"])] = None
    elif content == "bad_order_id":
        obj["order_id"] = obj["order_id"].replace("TB-", "")
    elif content == "amount_text":
        obj["amount_rs"] = "Rs %d" % (obj["amount_rs"] if obj["amount_rs"] is not None else 250)
    elif content == "nan_amount":
        obj["amount_rs"] = float("nan")
    if content == "not_object":
        return json.dumps([obj])
    return json.dumps(obj)


def wrap(text, wrapper, rng):
    if wrapper == "fence":
        return "```json\n" + text + "\n```"
    if wrapper == "prose":
        return "Here is the JSON you asked for:\n" + text + "\nLet me know if you need anything else."
    if wrapper == "trailing_comma":
        end = text.rstrip().rstrip("]")
        closing = text[len(end):]
        return end[:-1] + ",}" + closing
    if wrapper == "truncated":
        return text[:int(len(text) * rng.uniform(0.4, 0.85))]
    return text


def build(seed=DEFAULT_SEED, n=300):
    """Return {"outputs": [...], "truth": [...]} for this seed. Nothing is written.

    outputs: message_id, message, raw_output (what the pipeline receives).
    truth: message_id, wrapper, content, valid, and the true fields.
    """
    rng = random.Random(seed)
    outputs, truth = [], []
    used = set()
    for i in range(1, n + 1):
        while True:
            order_id = "TB-%05d" % rng.randint(10000, 99999)
            if order_id not in used:
                used.add(order_id)
                break
        refund = rng.random() < 0.55
        amount = rng.choice([120, 180, 240, 260, 310, 420, 560]) if (refund or rng.random() < 0.3) else None
        if refund and rng.random() < 0.15:
            amount = None
        fields = {
            "order_id": order_id,
            "issue": rng.choice(ISSUES),
            "refund_requested": refund,
            "amount_rs": amount,
            "severity": rng.choice([1, 2, 2, 3, 3, 3, 4, 5]),
        }
        wrapper, content = pick(WRAPPERS, rng), pick(CONTENT, rng)
        mid = "M%04d" % i
        outputs.append({"message_id": mid, "message": message_for(fields, rng),
                        "raw_output": wrap(damage(fields, content, rng), wrapper, rng)})
        row = {"message_id": mid, "wrapper": wrapper, "content": content,
               "valid": wrapper != "truncated" and content == "none"}
        row.update(fields)
        truth.append(row)
    return {"outputs": outputs, "truth": truth}


FIXTURE_INFO = {
    "file": "outputs.csv",
    "raw_output_source": "simulated",
    "model": "none: no model was called",
    "prompt": "Read the customer message. Reply with only a JSON object with keys order_id (TB- and 5 digits), "
              "issue (one of late, missing_item, wrong_item, cold_food, other), refund_requested (true or false), "
              "amount_rs (a number, or null if no amount is given) and severity (an integer from 1 to 5).",
    "temperature": "not applicable",
    "date": "not applicable",
    "how": "make_data.py writes the true fields as JSON, then applies one wrapper (none, code fence, prose, "
           "trailing comma, truncated) and one content problem (or none) chosen with a seeded random generator.",
    "seed": DEFAULT_SEED,
}


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    data = os.path.join(here, "data")
    os.makedirs(data, exist_ok=True)
    path = os.path.join(data, "outputs.csv")
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["message_id", "message", "raw_output"])
        w.writeheader()
        w.writerows(build()["outputs"])
    with open(os.path.join(data, "fixture.json"), "w") as f:
        json.dump(FIXTURE_INFO, f, indent=2)
        f.write("\n")
    print("wrote", path)


if __name__ == "__main__":
    main()
