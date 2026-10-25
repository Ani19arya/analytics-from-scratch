"""Solution: catch made-up numbers in an AI-written summary."""
import csv
import os
import re

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

# A number: digits with optional thousands commas, optional decimals.
NUMBER = re.compile(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?")


def load_csv(name, data_dir=DATA):
    with open(os.path.join(data_dir, name), newline="") as f:
        return list(csv.DictReader(f))


def extract_numbers(sentence):
    """Return [(value, decimals), ...] in the order they appear.

    decimals is how many digits follow the decimal point as written, so we know
    how precisely the number was stated.
    """
    out = []
    for m in NUMBER.finditer(sentence):
        raw = m.group(0).replace(",", "")
        decimals = len(raw.split(".")[1]) if "." in raw else 0
        out.append((float(raw), decimals))
    return out


def compute_metrics(rows):
    """The true value of every metric the summary is allowed to mention."""
    rev = [int(r["revenue"]) for r in rows]
    total = sum(rev)

    def region(name):
        return sum(int(r["revenue"]) for r in rows if r["region"] == name)

    def month(name):
        return sum(int(r["revenue"]) for r in rows if r["month"] == name)

    jan, jun = month("Jan"), month("Jun")
    return {
        "total_revenue": total,
        "order_count": len(rows),
        "avg_order_value": total / len(rows),
        "region_count": len(set(r["region"] for r in rows)),
        "north_revenue": region("North"),
        "south_revenue": region("South"),
        "west_revenue": region("West"),
        "north_share_pct": region("North") / total * 100,
        "jan_revenue": jan,
        "jun_revenue": jun,
        "growth_pct": (jun - jan) / jan * 100,
    }


def matches(claimed, decimals, actual):
    """A stated number matches if the true value rounds to it at the stated precision."""
    return abs(actual - claimed) <= 0.5 * 10 ** (-decimals) + 1e-9


def check_summary(rows, summary):
    """Return one dict per number: sentence_id, metric, claimed, actual, ok."""
    metrics = compute_metrics(rows)
    results = []
    for s in summary:
        names = s["metrics"].split(";")
        numbers = extract_numbers(s["sentence"])
        if len(names) != len(numbers):
            raise ValueError("%s: %d metrics but %d numbers" % (s["sentence_id"], len(names), len(numbers)))
        for name, (claimed, decimals) in zip(names, numbers):
            actual = metrics[name]
            results.append({
                "sentence_id": s["sentence_id"],
                "metric": name,
                "claimed": claimed,
                "actual": actual,
                "ok": matches(claimed, decimals, actual),
            })
    return results


def main():
    for r in check_summary(load_csv("orders.csv"), load_csv("ai_summary.csv")):
        flag = "ok  " if r["ok"] else "FLAG"
        print(flag, r["sentence_id"], r["metric"].ljust(16), "claimed", r["claimed"], "actual", round(r["actual"], 2))


if __name__ == "__main__":
    main()
