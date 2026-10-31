"""Build the data for lesson 06-04: one week of SYNTHETIC customer reviews, SIMULATED summaries,
a FICTIONAL rate card, a toy vocabulary and a tiny made-up next-token table.

Nothing here comes from a real model or a real price list:

- reviews.csv: made-up reviews of Tiffinbell, a fictional food delivery app.
- The summary column is SIMULATED. No model was called (data/fixture.json says so).
  Each summary is written from the same template as its review, so it is as long
  as a one-sentence summary would be.
- rate_card.csv: FICTIONAL example prices for two made-up models. They are not
  the prices of any real provider.
- vocab.csv: the word list of the lesson's TOY tokenizer. Real tokenizers learn
  their vocabulary from data and split text differently.
- next_token.csv: made-up scores (logits) for the next word after two prompts.

Run: python3 make_data.py
"""
import csv
import json
import os
import random

DEFAULT_SEED = 604
N_REVIEWS = 300

INSTRUCTIONS = ("Summarise this customer review in one sentence. Say if the customer is happy "
                "or unhappy, and name the main problem if there is one.")

# Common words the toy tokenizer keeps whole. Every other word is cut into pieces of 4 letters.
VOCAB = sorted(set("""
a about after again all also am an and any are arrived as at back be because been but by
can cold come customer delivery did dinner do does each extra fast find food for fresh from
get give good great had happy has have hot i if in is it item late later lunch main make me
minutes missing more much my name no not of on one only or order ordered our out please problem
quick rider say sentence so soggy some spicy still than thank thanks that the their them then there
they this time to too unhappy up very wants was we well were what when where which who will
with would wrong you your again late refund money price paid small portion taste tasty loved
review summarise sad again box bag spilled leaked packed nice warm on time while however
""".split()))

DISHES = ["paneer tikka", "dal makhani", "veg biryani", "chicken thali", "masala dosa",
          "poha", "misal pav", "rajma chawal", "aloo paratha", "curd rice"]
CITIES = ["Pune", "Nashik", "Nagpur", "Mumbai"]
HINGLISH = ["khana thanda tha", "bahut late aaya", "ekdum mast tha", "paisa wasool", "thoda kam tha"]

# (review wording, summary wording). Slots: {dish}, {mins}, {amount}, {city}, {hing}.
TEMPLATES = [
    ("The {dish} arrived cold and {mins} minutes late. Not happy at all.",
     "The customer is unhappy because the {dish} arrived cold and {mins} minutes late."),
    ("Loved the {dish}, it was hot and fresh. The rider was quick and polite. Thank you!",
     "The customer is happy: the {dish} was hot and fresh and the delivery was quick."),
    ("My order was missing the {dish}. I paid Rs {amount} and want my money back.",
     "The customer is unhappy because the {dish} was missing and wants a refund of Rs {amount}."),
    ("The bag leaked and the {dish} spilled everywhere. Please pack it better.",
     "The customer is unhappy because the bag leaked and the {dish} spilled; they ask for better packing."),
    ("Great taste but the portion of {dish} was too small for Rs {amount}.",
     "The customer liked the taste but is unhappy that the {dish} portion was small for Rs {amount}."),
    ("{hing}! The {dish} from the {city} kitchen.",
     "The customer wrote in Hinglish about the {dish} from the {city} kitchen; the main point is: {hing}."),
    ("Ordered {dish} for lunch, it came on time and was still warm. Good service.",
     "The customer is happy: the {dish} came on time and was still warm."),
    ("Wrong item. I ordered {dish} and got something else. The rider said to call support.",
     "The customer is unhappy because they got the wrong item instead of the {dish}."),
    ("The {dish} was far too spicy and the raita was missing. Delivery in {city} was fast though.",
     "The customer is unhappy that the {dish} was too spicy and the raita was missing, although delivery was fast."),
    ("Tiffinbell app crashed twice while I was paying Rs {amount}, then the order went through.",
     "The customer is unhappy that the app crashed twice during payment, but the order went through."),
]

RATE_CARD = [
    {"model": "example-small", "input_per_million": "0.50", "output_per_million": "2.00",
     "note": "fictional example price, not any real provider"},
    {"model": "example-large", "input_per_million": "5.00", "output_per_million": "20.00",
     "note": "fictional example price, not any real provider"},
]

# Made-up scores for the next word. A higher logit means the word is more likely.
NEXT_TOKEN = [
    ("Your order was", "delivered", 2.2),
    ("Your order was", "late", 1.4),
    ("Your order was", "cold", 0.8),
    ("Your order was", "cancelled", 0.3),
    ("Your order was", "wonderful", -1.0),
    ("Overall the customer is", "happy", 1.1),
    ("Overall the customer is", "unhappy", 1.0),
    ("Overall the customer is", "angry", 0.4),
    ("Overall the customer is", "confused", 0.1),
]


def fill(text, slots):
    out = text.format(**slots)
    return out[0].upper() + out[1:]


def build(seed=DEFAULT_SEED, n=N_REVIEWS):
    """Return {"reviews", "rate_card", "vocab", "next_token"} for this seed. Nothing is written."""
    rng = random.Random(seed)
    reviews = []
    for i in range(1, n + 1):
        review, summary = rng.choice(TEMPLATES)
        slots = {
            "dish": rng.choice(DISHES),
            "mins": rng.choice([25, 35, 40, 50, 70]),
            "amount": rng.choice([149, 199, 249, 329, 449]),
            "city": rng.choice(CITIES),
            "hing": rng.choice(HINGLISH),
        }
        reviews.append({"review_id": "R%04d" % i, "text": fill(review, slots), "summary": fill(summary, slots)})
    return {
        "reviews": reviews,
        "rate_card": [dict(r) for r in RATE_CARD],
        "vocab": list(VOCAB),
        "next_token": [{"context": c, "token": t, "logit": "%.1f" % z} for c, t, z in NEXT_TOKEN],
    }


FIXTURE_INFO = {
    "file": "reviews.csv",
    "summary_source": "simulated",
    "model": "none: no model was called",
    "prompt": INSTRUCTIONS,
    "prompt_version": "v1",
    "temperature": "not applicable",
    "date": "not applicable",
    "how": "make_data.py writes each summary from the same template and slot values as its review.",
    "rate_card": "rate_card.csv holds fictional example prices, not any real provider's prices",
    "seed": DEFAULT_SEED,
}


def write_csv(path, rows, fields):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    data = os.path.join(here, "data")
    os.makedirs(data, exist_ok=True)
    d = build()
    write_csv(os.path.join(data, "reviews.csv"), d["reviews"], ["review_id", "text", "summary"])
    write_csv(os.path.join(data, "rate_card.csv"), d["rate_card"],
              ["model", "input_per_million", "output_per_million", "note"])
    write_csv(os.path.join(data, "vocab.csv"), [{"word": w} for w in d["vocab"]], ["word"])
    write_csv(os.path.join(data, "next_token.csv"), d["next_token"], ["context", "token", "logit"])
    with open(os.path.join(data, "fixture.json"), "w") as f:
        json.dump(FIXTURE_INFO, f, indent=2)
        f.write("\n")
    print("wrote", data)


if __name__ == "__main__":
    main()
