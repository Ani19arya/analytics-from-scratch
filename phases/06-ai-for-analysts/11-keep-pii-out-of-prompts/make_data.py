"""Build the data for lesson 06-11: SYNTHETIC support messages to Tiffinbell (a fictional food
delivery app) with personal data planted in them, and the truth about what was planted.

No real person's data is used:
- Every email address uses example.com, example.net or example.org, which are reserved for
  documentation (RFC 2606), so they cannot belong to anyone.
- Phone numbers are random digits in the shape of Indian mobile and US numbers. US numbers use
  the 555 exchange. They are invented for this lesson; never call or message a number from a dataset.
- Card numbers are random digits made to pass the Luhn check. They are not real cards.
- Names are first names only, picked from a short list.

Files:
- messages.csv: message_id, text.
- pii_truth.csv: every planted email, phone, card and spelled-out email, as written, with
  its normalised form (the key a stable placeholder is built from).
- decoys.csv: things that look like personal data but are not, and must survive redaction:
  order ids, tracking numbers, dates, voucher codes that fail the Luhn check, social handles,
  the last four digits of a card.

Run: python3 make_data.py
"""
import csv
import os
import random

DEFAULT_SEED = 611
N_MESSAGES = 240

FIRST = ["asha", "rohan", "meera", "kabir", "nisha", "dev", "tara", "imran", "sana", "vikram",
         "leela", "arjun", "zoya", "neel", "ira", "sam", "maya", "omar", "ruth", "jay"]
SURNAME_INITIAL = list("abcdefghijklmnoprstvw")
DOMAINS = ["example.com", "example.net", "example.org"]
US_AREAS = ["212", "415", "646", "312", "206", "617"]


def luhn_check_digit(body):
    """The digit that makes body + digit pass the Luhn check."""
    total = 0
    for i, ch in enumerate(reversed(body)):
        d = int(ch)
        if i % 2 == 0:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return str((10 - total % 10) % 10)


def luhn_valid(digits):
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return len(digits) > 0 and total % 10 == 0


def make_customer(rng, i):
    first = FIRST[i % len(FIRST)]
    sep = rng.choice([".", "_", ""])
    local = "%s%s%s%d" % (first, sep, rng.choice(SURNAME_INITIAL), rng.randint(1, 99))
    email = "%s@%s" % (local, rng.choice(DOMAINS))
    if rng.random() < 0.25:
        digits = rng.choice(US_AREAS) + "555" + "01%02d" % rng.randint(0, 99)
        country = "US"
    else:
        digits = rng.choice("6789") + "".join(rng.choice("0123456789") for _ in range(9))
        country = "IN"
    return {"name": first.capitalize(), "email": email, "phone_digits": digits, "country": country}


def write_phone(c, rng):
    d = c["phone_digits"]
    if c["country"] == "US":
        forms = ["(%s) %s-%s" % (d[:3], d[3:6], d[6:]), "%s-%s-%s" % (d[:3], d[3:6], d[6:]),
                 "%s.%s.%s" % (d[:3], d[3:6], d[6:]), "+1 %s %s %s" % (d[:3], d[3:6], d[6:]), "+1" + d]
    else:
        forms = ["+91 %s %s" % (d[:5], d[5:]), "+91-" + d, "+91" + d, "0" + d, "%s %s" % (d[:5], d[5:]),
                 d, "0091 %s %s" % (d[:5], d[5:])]
    return rng.choice(forms)


def write_email(c, rng):
    email = c["email"]
    if rng.random() < 0.2:
        local, domain = email.split("@")
        email = local.capitalize() + "@" + domain.capitalize()
    return email


def make_card(rng, sep):
    body = rng.choice("45") + "".join(rng.choice("0123456789") for _ in range(14))
    digits = body + luhn_check_digit(body)
    return sep.join(digits[i:i + 4] for i in range(0, 16, 4)), digits


def make_voucher(rng):
    while True:
        digits = "".join(rng.choice("0123456789") for _ in range(16))
        if not luhn_valid(digits) and digits[0] not in "0":
            return " ".join(digits[i:i + 4] for i in range(0, 16, 4))


def order_id(rng):
    # Tiffinbell order ids are TB- and 10 digits. Some start with 6 to 9, like a mobile number.
    return "TB-" + rng.choice("123456789") + "".join(rng.choice("0123456789") for _ in range(9))


def tracking(rng):
    # 13 digits. About one random number in ten passes the Luhn check and would look like a
    # card, so the generator keeps only those that fail: they are decoys that must survive.
    while True:
        digits = "".join(rng.choice("0123456789") for _ in range(13))
        if not luhn_valid(digits):
            return digits


def a_date(rng):
    day = rng.randint(1, 30)
    return rng.choice(["2026-10-%02d" % day, "%02d/10/2026" % day])


def build(seed=DEFAULT_SEED, n=N_MESSAGES):
    """Return {"messages", "pii_truth", "decoys"} for this seed. Nothing is written."""
    rng = random.Random(seed)
    customers = [make_customer(rng, i) for i in range(60)]
    messages, truth, decoys = [], [], []

    for i in range(1, n + 1):
        mid = "M%04d" % i
        c = rng.choice(customers)
        kind = rng.randrange(12)
        pii, dec = [], []
        if kind == 0:
            p, o = write_phone(c, rng), order_id(rng)
            text = "Hi, my order %s has not arrived. Call me on %s please." % (o, p)
            pii, dec = [("phone", p)], [("order_id", o)]
        elif kind == 1:
            e, o = write_email(c, rng), order_id(rng)
            text = "Please send the invoice for %s to %s, thanks." % (o, e)
            pii, dec = [("email", e)], [("order_id", o)]
        elif kind == 2:
            card, _ = make_card(rng, rng.choice([" ", "-", ""]))
            o, amt = order_id(rng), rng.choice(["Rs 249", "Rs 1,499", "Rs 329"])
            text = "I paid %s with card %s but %s still shows unpaid." % (amt, card, o)
            pii, dec = [("card", card)], [("order_id", o), ("amount", amt)]
        elif kind == 3:
            e = c["email"]
            written = e.replace("@", "%40") if rng.random() < 0.5 else e
            text = "The reset link does not work: https://app.tiffinbell.example/reset?user=%s&ref=app" % written
            pii = [("email", written)]
        elif kind == 4:
            t, d, p = tracking(rng), a_date(rng), write_phone(c, rng)
            text = "This is %s. Tracking %s says delivered on %s but nothing came. %s" % (c["name"], t, d, p)
            pii, dec = [("phone", p)], [("tracking", t), ("date", d)]
        elif kind == 5:
            v, o = make_voucher(rng), order_id(rng)
            text = "Voucher %s did not apply to order %s." % (v, o)
            dec = [("voucher", v), ("order_id", o)]
        elif kind == 6:
            us = [x for x in customers if x["country"] == "US"]
            other = rng.choice(us) if us else c
            p, e = write_phone(other, rng), write_email(c, rng)
            text = "My son in the US placed it, his number is %s. Reply to %s." % (p, e)
            pii = [("phone", p), ("email", e)]
        elif kind == 7:
            local, domain = c["email"].split("@")
            spelled = "%s at %s dot %s" % (local.replace(".", " dot "), domain.split(".")[0], domain.split(".")[1])
            text = "The app said to DM @tiffinbell_care. My email is %s if you need it." % spelled
            pii, dec = [("spelled_email", spelled)], [("handle", "@tiffinbell_care")]
        elif kind == 8:
            o, d = order_id(rng), a_date(rng)
            text = "Order %s on %s at 1:30 pm was perfect, thank you!" % (o, d)
            dec = [("order_id", o), ("date", d)]
        elif kind == 9:
            e, p = write_email(c, rng), write_phone(c, rng)
            text = "Write to me at mailto:%s or call %s after 6 pm." % (e, p)
            pii = [("email", e), ("phone", p)]
        elif kind == 10:
            last4, o = "%04d" % rng.randint(0, 9999), order_id(rng)
            text = "My card ending %s was charged twice for %s." % (last4, o)
            dec = [("last4", last4), ("order_id", o)]
        else:
            o, t = order_id(rng), tracking(rng)
            text = "Courier changed: order %s now has tracking number %s." % (o, t)
            dec = [("order_id", o), ("tracking", t)]
        messages.append({"message_id": mid, "text": text})
        for k, v in pii:
            truth.append({"message_id": mid, "kind": k, "value": v, "norm": normalise(k, v)})
        for k, v in dec:
            decoys.append({"message_id": mid, "kind": k, "value": v})
    return {"messages": messages, "pii_truth": truth, "decoys": decoys}


def normalise(kind, value):
    """The key that makes two spellings of one value share a placeholder."""
    if kind == "email":
        return value.replace("%40", "@").lower()
    digits = "".join(ch for ch in value if ch.isdigit())
    if kind == "phone":
        return digits[-10:]
    if kind == "card":
        return digits
    return value.lower()


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
    write_csv(os.path.join(data, "messages.csv"), d["messages"], ["message_id", "text"])
    write_csv(os.path.join(data, "pii_truth.csv"), d["pii_truth"], ["message_id", "kind", "value", "norm"])
    write_csv(os.path.join(data, "decoys.csv"), d["decoys"], ["message_id", "kind", "value"])
    print("wrote", data)


if __name__ == "__main__":
    main()
