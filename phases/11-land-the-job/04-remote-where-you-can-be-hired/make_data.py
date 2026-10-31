"""Build the synthetic data for the remote-roles lesson.

data/remote_postings.csv  posting_id, company, title, location   (SYNTHETIC: invented companies and lines)
data/places.csv           name, country   (country names, short forms and cities, lower case)
data/regions.csv          region, country (which countries this lesson counts inside each region name)

places.csv and regions.csv are a teaching map, not a legal or official definition: employers
draw regions such as EMEA or APAC in their own way, so read the posting.
The real numbers in this lesson live in data/real_snapshot_2026-10-31.json, which this script
does not touch.

Seed 0 (the default) is the hand written lesson data, for a job seeker based in India. Any other
seed generates new postings for another home country, for the second-dataset test.
build(seed) returns {"home", "postings", "places", "regions", "truth"} without writing files.
Run from the lesson folder: python3 make_data.py
"""
import csv
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
SEED = 0

COUNTRIES = {
    "India": ["india", "bengaluru", "bangalore", "hyderabad", "pune", "mumbai"],
    "United States": ["united states", "usa", "us", "new york", "seattle", "indianapolis"],
    "United Kingdom": ["united kingdom", "uk", "london", "manchester"],
    "Canada": ["canada", "toronto"],
    "Germany": ["germany", "berlin"],
    "Mexico": ["mexico", "mexico city"],
    "Spain": ["spain", "madrid"],
    "Poland": ["poland", "warsaw"],
    "Brazil": ["brazil", "sao paulo"],
    "Philippines": ["philippines", "manila"],
    "Singapore": ["singapore"],
    "Australia": ["australia", "sydney"],
    "Ireland": ["ireland", "dublin"],
}
REGIONS = {
    "apac": ["India", "Singapore", "Philippines", "Australia"],
    "south asia": ["India"],
    "emea": ["United Kingdom", "Germany", "Spain", "Poland", "Ireland"],
    "europe": ["United Kingdom", "Germany", "Spain", "Poland", "Ireland"],
    "eu": ["Germany", "Spain", "Poland", "Ireland"],
    "latam": ["Mexico", "Brazil"],
    "north america": ["United States", "Canada", "Mexico"],
    "americas": ["United States", "Canada", "Mexico", "Brazil"],
}

HOME = "India"
POSTINGS = [
    ("R01", "Lattice Fern", "Data Analyst", "Remote - India"),
    ("R02", "Lattice Fern", "Product Analyst", "Bengaluru (Remote)"),
    ("R03", "Coldharbour Pay", "Business Analyst", "Remote, US or India"),
    ("R04", "Mistral Pine Labs", "Data Analyst", "Remote (APAC)"),
    ("R05", "Orchard Signal", "Analytics Engineer", "Remote, worldwide"),
    ("R06", "Orchard Signal", "Data Analyst", "Anywhere (Remote)"),
    ("R07", "Bramwell Health", "Data Analyst", "Remote"),
    ("R08", "Bramwell Health", "Operations Analyst", "Fully remote"),
    ("R09", "Quillon Retail", "Marketing Analyst", "Remote"),
    ("R10", "Quillon Retail", "BI Analyst", "Remote - flexible hours"),
    ("R11", "Tidewell Freight", "Supply Chain Analyst", "Remote"),
    ("R12", "Coldharbour Pay", "Risk Analyst", "Remote - US"),
    ("R13", "Coldharbour Pay", "Financial Analyst", "Remote, anywhere in the United States"),
    ("R14", "Harlow Kite", "Data Analyst", "Remote - Indianapolis, IN"),
    ("R15", "Harlow Kite", "Product Analyst", "Remote in Canada"),
    ("R16", "Sennet Media", "Audience Analyst", "Remote (EMEA)"),
    ("R17", "Sennet Media", "Data Analyst", "Remote - UK"),
    ("R18", "Vellum Bay", "Business Analyst", "Remote, EU only"),
    ("R19", "Vellum Bay", "Data Analyst", "Remote (LATAM)"),
    ("R20", "Tidewell Freight", "Pricing Analyst", "Remote - North America"),
    ("R21", "Penhallow Insurance", "Claims Analyst", "Remote - Germany"),
    ("R22", "Penhallow Insurance", "Data Analyst", "Toronto, Canada (Remote)"),
]
TRUTH = {
    "R01": "based_in_country", "R02": "based_in_country", "R03": "based_in_country",
    "R04": "region_includes", "R05": "worldwide", "R06": "worldwide",
    "R07": "no_country", "R08": "no_country", "R09": "no_country", "R10": "no_country", "R11": "no_country",
    "R12": "other_country", "R13": "other_country", "R14": "other_country", "R15": "other_country",
    "R16": "other_country", "R17": "other_country", "R18": "other_country", "R19": "other_country",
    "R20": "other_country", "R21": "other_country", "R22": "other_country",
}

HOMES = ["India", "Poland", "Canada", "Brazil", "United Kingdom", "Germany", "Philippines"]
COMPANIES = ["Ashbourne Loop", "Birchmere Data", "Cranleigh Pay", "Dunmoor Health", "Edgecote Media",
             "Fallowfield Retail", "Greystoke Freight", "Hollins Mark"]
TITLES = ["Data Analyst", "Business Analyst", "Product Analyst", "BI Analyst", "Operations Analyst"]
WORLDWIDE = ["Remote, worldwide", "Anywhere (Remote)", "Remote - work from anywhere", "Global remote"]
NO_COUNTRY = ["Remote", "Fully remote", "Remote - flexible hours", "Remote first team"]


def display(name):
    """How a place is written in a location line."""
    return name.upper() if len(name) <= 3 else name.title()


def build(seed=SEED):
    """{"home", "postings": [[id, company, title, location]], "places": [[name, country]],
    "regions": [[region, country]], "truth": {posting_id: class}}."""
    places = sorted([name, c] for c, names in COUNTRIES.items() for name in names)
    regions = sorted([r, c] for r, cs in REGIONS.items() for c in cs)
    if seed == SEED:
        return {"home": HOME, "postings": [list(p) for p in POSTINGS], "places": places,
                "regions": regions, "truth": dict(TRUTH)}
    rng = random.Random(seed)
    home = rng.choice(HOMES)
    others = [c for c in COUNTRIES if c != home]
    mine_regions = [r for r, cs in REGIONS.items() if home in cs]
    other_regions = [r for r, cs in REGIONS.items() if home not in cs]
    postings, truth = [], {}
    for i in range(1, rng.randint(18, 30) + 1):
        label = rng.choice(["based_in_country", "region_includes", "worldwide",
                            "no_country", "no_country", "other_country", "other_country", "other_country"])
        if label == "region_includes" and not mine_regions:
            label = "no_country"
        if label == "based_in_country":
            place = display(rng.choice(COUNTRIES[home]))
            loc = rng.choice(["Remote - %s", "%s (Remote)", "Remote, %s or " % display(rng.choice(others)) + "%s"]) % place
        elif label == "region_includes":
            loc = rng.choice(["Remote (%s)", "Remote - %s"]) % display(rng.choice(mine_regions))
        elif label == "worldwide":
            loc = rng.choice(WORLDWIDE)
        elif label == "no_country":
            loc = rng.choice(NO_COUNTRY)
        else:
            kind = rng.choice(["country", "region", "anywhere", "city"])
            other = rng.choice(others)
            if kind == "region" and other_regions:
                loc = "Remote (%s)" % display(rng.choice(other_regions))
            elif kind == "anywhere":
                loc = "Remote, anywhere in %s" % display(COUNTRIES[other][0])
            elif kind == "city":
                loc = "%s, remote" % display(rng.choice(COUNTRIES[other]))
            else:
                loc = "Remote - %s" % display(COUNTRIES[other][0])
        pid = "R%02d" % i
        postings.append([pid, rng.choice(COMPANIES), rng.choice(TITLES), loc])
        truth[pid] = label
    return {"home": home, "postings": postings, "places": places, "regions": regions, "truth": truth}


def write_csv(path, header, rows):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def main():
    data = build()
    d = os.path.join(HERE, "data")
    os.makedirs(d, exist_ok=True)
    write_csv(os.path.join(d, "remote_postings.csv"), ["posting_id", "company", "title", "location"], data["postings"])
    write_csv(os.path.join(d, "places.csv"), ["name", "country"], data["places"])
    write_csv(os.path.join(d, "regions.csv"), ["region", "country"], data["regions"])
    print("wrote %d postings, %d places, %d region rows (home: %s)"
          % (len(data["postings"]), len(data["places"]), len(data["regions"]), data["home"]))


if __name__ == "__main__":
    main()
