"""Exercise: remote, really. Classify remote postings by where they can hire from.

Fill in named, classify_location, summary, open_to_me and tied_to. padded, read, load and
main are done for you. Then run: python3 test_lesson.py
"""
import csv
import os
import re

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
HOME = "India"

CLASSES = ["based_in_country", "region_includes", "worldwide", "no_country", "other_country"]
OPEN = {"based_in_country", "region_includes", "worldwide"}
WORLDWIDE = re.compile(r"\b(?:anywhere|worldwide|global|globally)\b")


def padded(text):
    """Lower case, every run of non letters and digits turned into one space, padded with spaces,
    so ' india ' can be found as a whole phrase and never inside ' indianapolis '."""
    return " " + " ".join(re.sub(r"[^a-z0-9]+", " ", text.lower()).split()) + " "


def named(location, places, regions):
    """(countries, regions): the sets of country names and region names the location line names.
    places rows have name, country; regions rows have region, country."""
    # TODO: match each place name and region name as a whole phrase in padded(location).
    raise NotImplementedError


def classify_location(location, home, places, regions):
    """One of CLASSES for a candidate based in home."""
    # TODO: decide the order. What should 'Remote, anywhere in the United States' be?
    raise NotImplementedError


def summary(postings, home, places, regions):
    """{class: count} with every class in CLASSES present, zeros included."""
    # TODO
    raise NotImplementedError


def open_to_me(postings, home, places, regions):
    """posting_ids, in file order, whose class is in OPEN."""
    # TODO
    raise NotImplementedError


def tied_to(postings, home, places, regions):
    """{country: count} over other_country postings, each posting counting once per country it names."""
    # TODO
    raise NotImplementedError


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
