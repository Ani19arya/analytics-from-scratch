"""Solution: classify remote postings by where they can hire from, for one home country.

Run from the lesson folder: python3 solution/solution.py
"""
import csv
import os
import re

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
HOME = "India"

CLASSES = ["based_in_country", "region_includes", "worldwide", "no_country", "other_country"]
OPEN = {"based_in_country", "region_includes", "worldwide"}
WORLDWIDE = re.compile(r"\b(?:anywhere|worldwide|global|globally)\b")


def padded(text):
    """Lower case, every run of non letters and digits turned into one space, padded with spaces,
    so ' india ' can be found as a whole phrase and never inside ' indianapolis '."""
    return " " + " ".join(re.sub(r"[^a-z0-9]+", " ", text.lower()).split()) + " "


def named(location, places, regions):
    """(countries, regions): the sets the location line names, matched as whole phrases.
    places rows have name, country; regions rows have region, country."""
    text = padded(location)
    countries = {p["country"] for p in places if " " + p["name"] + " " in text}
    found = {r["region"] for r in regions if " " + r["region"] + " " in text}
    return countries, found


def classify_location(location, home, places, regions):
    """One of CLASSES for a candidate based in home. A named place beats a worldwide word,
    because 'anywhere in the United States' is tied to the United States."""
    countries, found = named(location, places, regions)
    if home in countries:
        return "based_in_country"
    if any(r["region"] in found and r["country"] == home for r in regions):
        return "region_includes"
    if countries or found:
        return "other_country"
    if WORLDWIDE.search(location.lower()):
        return "worldwide"
    return "no_country"


def summary(postings, home, places, regions):
    """{class: count} with every class in CLASSES present, zeros included."""
    out = {c: 0 for c in CLASSES}
    for p in postings:
        out[classify_location(p["location"], home, places, regions)] += 1
    return out


def open_to_me(postings, home, places, regions):
    """posting_ids, in file order, whose location line includes home: its country, a region that
    contains it, or worldwide. 'Remote' with no country is not on this list: it needs a question."""
    return [p["posting_id"] for p in postings
            if classify_location(p["location"], home, places, regions) in OPEN]


def tied_to(postings, home, places, regions):
    """{country: count} over other_country postings: which countries they name, each posting
    counting once per country. Regions are left out, since a region is not one country."""
    out = {}
    for p in postings:
        if classify_location(p["location"], home, places, regions) == "other_country":
            for c in named(p["location"], places, regions)[0]:
                out[c] = out.get(c, 0) + 1
    return out


def read(name, data_dir=DATA):
    with open(os.path.join(data_dir, name), newline="") as f:
        return list(csv.DictReader(f))


def load(data_dir=DATA):
    return read("remote_postings.csv", data_dir), read("places.csv", data_dir), read("regions.csv", data_dir)


def main():
    postings, places, regions = load()
    for p in postings:
        print("%s  %-40s %s" % (p["posting_id"], p["location"], classify_location(p["location"], HOME, places, regions)))
    print(summary(postings, HOME, places, regions))
    print("open to someone in %s:" % HOME, open_to_me(postings, HOME, places, regions))


if __name__ == "__main__":
    main()
