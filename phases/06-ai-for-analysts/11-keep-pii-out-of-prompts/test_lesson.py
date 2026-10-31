"""Tests. Default: checks exercise.py. With CHECK_SOLUTION=1: checks solution/solution.py.

The expected answers do not come from a second regex. They come from what make_data.py
planted: every email, phone and card it wrote into a message (must be gone), every
look-alike it wrote (order ids, tracking numbers, dates, vouchers, handles: must survive),
and every spelled-out email (the message must be blocked). The same checks run on a second
set of messages built in memory from another seed, plus hand-made tricky cases.
"""
import csv
import importlib.util
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "solution", "solution.py") if os.environ.get("CHECK_SOLUTION") == "1" else os.path.join(HERE, "exercise.py")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


lesson = load("lesson", TARGET)
make_data = load("make_data", os.path.join(HERE, "make_data.py"))

OTHER_SEED = 1611
PLACEHOLDER = re.compile(r"\[(EMAIL|PHONE|CARD)_\d+\]")
KIND_LABEL = {"email": "EMAIL", "phone": "PHONE", "card": "CARD"}


def committed():
    out = {}
    for name in ("messages", "pii_truth", "decoys"):
        with open(os.path.join(HERE, "data", name + ".csv"), newline="") as f:
            out[name] = list(csv.DictReader(f))
    return out


def ref_luhn(digits):
    """Luhn by a second route: the doubled-digit sums looked up in a table."""
    doubled = [0, 2, 4, 6, 8, 1, 3, 5, 7, 9]
    ds = [int(c) for c in digits if c.isdigit()]
    if not ds:
        return False
    s = sum(doubled[d] if i % 2 else d for i, d in enumerate(reversed(ds)))
    return s % 10 == 0


def red(text):
    return lesson.redact(text, {})


class TestLuhn(unittest.TestCase):
    def test_known_numbers(self):
        self.assertTrue(lesson.luhn_ok("79927398713"), "79927398713 is the textbook number that passes Luhn")
        self.assertFalse(lesson.luhn_ok("79927398710"))
        self.assertTrue(lesson.luhn_ok("4111-1111-1111-1111"), "ignore hyphens and spaces before checking")
        self.assertFalse(lesson.luhn_ok(""), "no digits cannot pass")
        self.assertTrue(lesson.luhn_ok("0"), "a single 0 sums to 0, which ends in 0")

    def test_matches_reference(self):
        for n in ["4539 1488 0343 6467", "4539148803436468", "6011000990139424", "1234567812345670", "9199734782221"]:
            self.assertEqual(lesson.luhn_ok(n), ref_luhn(n), "Luhn result differs for %s" % n)


class TestTrickyCases(unittest.TestCase):
    def test_empty_and_clean(self):
        self.assertEqual(red(""), "")
        self.assertEqual(lesson.audit(""), [])
        self.assertEqual(red("Thanks, the food was great!"), "Thanks, the food was great!")

    def test_emails_in_urls(self):
        self.assertEqual(red("Link: https://app.tiffinbell.example/reset?user=asha.k@example.com&ref=app"),
                         "Link: https://app.tiffinbell.example/reset?user=[EMAIL_1]&ref=app")
        self.assertEqual(red("user=asha.k%40example.com&x=1"), "user=[EMAIL_1]&x=1",
                         "%40 is an @ written for a URL: it is still an email")
        self.assertEqual(red("mailto:Dev_J9@Example.org"), "mailto:[EMAIL_1]")

    def test_handles_are_not_emails(self):
        self.assertEqual(red("DM us at @tiffinbell_care"), "DM us at @tiffinbell_care",
                         "a social handle has no local part or domain: leave it")

    def test_phone_formats(self):
        for p in ["+91 98450 12345", "+91-9845012345", "+919845012345", "09845012345", "98450 12345",
                  "9845012345", "0091 98450 12345", "(415) 555-0142", "415-555-0142", "415.555.0142",
                  "+1 415 555 0142", "+14155550142"]:
            self.assertEqual(red("Call %s now." % p), "Call [PHONE_1] now.", "phone not caught: %s" % p)

    def test_order_ids_tracking_dates_are_kept(self):
        for text in ["Order TB-9845012345 is late.", "Order #9845012345 is late.",
                     "Tracking 7712345678902 shows delivered.", "Delivered 2026-10-28 at 10:30.",
                     "Delivered 28/10/2026.", "Paid Rs 12,499 today.", "Card ending 4242 was charged."]:
            self.assertEqual(red(text), text, "this is not personal data and must survive: %r" % text)

    def test_cards_need_luhn(self):
        self.assertEqual(red("Card 4111 1111 1111 1111 was declined."), "Card [CARD_1] was declined.")
        self.assertEqual(red("Card 4111-1111-1111-1111."), "Card [CARD_1].")
        self.assertEqual(red("Voucher 1234 5678 9012 3456 failed."), "Voucher 1234 5678 9012 3456 failed.",
                         "a 16-digit voucher that fails Luhn is not a card")

    def test_phone_with_0091_is_a_phone_not_a_card(self):
        self.assertTrue(ref_luhn("00919728138703"))
        self.assertEqual(red("call 0091 97281 38703 after 6"), "call [PHONE_1] after 6",
                         "this passes Luhn by chance: look for phones before cards")

    def test_stable_placeholders(self):
        texts = ["Mail asha.k@example.com or 98450 12345", "Again: ASHA.K@EXAMPLE.COM, +91-9845012345",
                 "Other: ravi@example.net", "and asha.k%40example.com"]
        out, mapping = lesson.redact_all(texts)
        self.assertEqual(out, ["Mail [EMAIL_1] or [PHONE_1]", "Again: [EMAIL_1], [PHONE_1]",
                               "Other: [EMAIL_2]", "and [EMAIL_1]"],
                         "the same email or phone, however it is written, must get the same placeholder")
        self.assertEqual(mapping[("email", "asha.k@example.com")], "[EMAIL_1]")
        self.assertEqual(mapping[("phone", "9845012345")], "[PHONE_1]")

    def test_audit_blocks(self):
        with self.assertRaises(lesson.Blocked, msg="a spelled-out email must block the send"):
            lesson.send_or_block("Summarise: my email is asha dot k at example dot com")
        with self.assertRaises(lesson.Blocked, msg="the audit checks the whole prompt, instructions too"):
            lesson.send_or_block("Example: reply to priya@example.com.\n\nSummarise: [EMAIL_1] says hi")
        self.assertEqual(lesson.send_or_block("Summarise: [EMAIL_1] called from [PHONE_1]"),
                         "Summarise: [EMAIL_1] called from [PHONE_1]", "placeholders are clean: send them")
        kinds = [k for k, _ in lesson.audit("call +91 98450 12345, card 4111111111111111, x@example.com")]
        self.assertEqual(sorted(kinds), ["card", "email", "phone"])


class TestOnData(unittest.TestCase):
    def check(self, data, label):
        msgs = data["messages"]
        out, mapping = lesson.redact_all([m["text"] for m in msgs])
        self.assertEqual(len(out), len(msgs))
        by_id = {m["message_id"]: o for m, o in zip(msgs, out)}
        for t in data["pii_truth"]:
            text = by_id[t["message_id"]]
            if t["kind"] == "spelled_email":
                continue
            self.assertNotIn(t["value"], text, "%s %s: the %s %r leaked" % (label, t["message_id"], t["kind"], t["value"]))
            key = (t["kind"], t["norm"])
            self.assertIn(key, mapping, "%s: %s %r has no placeholder of the right kind" % (label, t["kind"], t["value"]))
            self.assertTrue(mapping[key].startswith("[" + KIND_LABEL[t["kind"]] + "_"),
                            "%s: %r should get a %s placeholder" % (label, t["value"], KIND_LABEL[t["kind"]]))
            self.assertIn(mapping[key], text)
        for d in data["decoys"]:
            self.assertIn(d["value"], by_id[d["message_id"]],
                          "%s %s: the %s %r is not personal data and was removed" % (label, d["message_id"], d["kind"], d["value"]))
        expected_blocked = {t["message_id"] for t in data["pii_truth"] if t["kind"] == "spelled_email"}
        for mid, text in by_id.items():
            blocked = bool(lesson.audit(text))
            self.assertEqual(blocked, mid in expected_blocked,
                             "%s %s: audit should %s this message" % (label, mid, "block" if mid in expected_blocked else "pass"))
        distinct = {(t["kind"], t["norm"]) for t in data["pii_truth"] if t["kind"] != "spelled_email"}
        self.assertEqual(len(set(mapping.values())), len(distinct),
                         "%s: one placeholder per distinct person value, no more, no less" % label)
        for o in out:
            for ph in PLACEHOLDER.findall(o):
                self.assertIn(ph, ("EMAIL", "PHONE", "CARD"))

    def test_committed(self):
        self.check(committed(), "committed data")

    def test_second_dataset(self):
        self.check(make_data.build(seed=OTHER_SEED), "seed %d" % OTHER_SEED)


if __name__ == "__main__":
    unittest.main()
