"""Build the synthetic data for the visa-aware search lesson.

data/postings.csv       posting_id, company, title, country, text
data/uscis_history.csv  employer_name, fiscal_year, state, new_approvals, continuing_approvals, denials
data/uk_register.csv    organisation_name, town, route
data/aliases.csv        company, filed_name

Everything in these four files is SYNTHETIC: every company, posting and count is invented to
teach the method. uscis_history.csv only borrows the shape of the counts the USCIS H-1B Employer
Data Hub publishes (one row per employer name as filed and fiscal year). uk_register.csv only
borrows the idea of the UK register of licensed sponsors (a list of organisation names).
The real numbers in this lesson live in data/real_snapshot_2026-10-31.json, which this script
does not touch.

Seed 0 (the default) is the hand written lesson data. Any other seed generates a new set from
the same phrase banks, for the second-dataset test. build(seed) returns the rows and the truth
without writing files. Run from the lesson folder: python3 make_data.py
"""
import csv
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
SEED = 0

POSTINGS = [
    ("V01", "Kestrel Ledger", "Data Analyst", "US",
     "Kestrel Ledger builds accounting software for small firms. "
     "About the role: you will own the weekly revenue report in SQL and Looker."),
    ("V02", "Kestrel Ledger", "Product Analyst", "US",
     "About the role: run experiments on our invoicing flow. H-1B sponsorship is available for this role."),
    ("V03", "Kestrel Ledger", "Business Analyst", "US",
     "About the role: map finance processes. Candidates must be authorized to work in the U.S."),
    ("V04", "Orrin Health", "Healthcare Data Analyst", "US",
     "About the role: build clinic utilisation dashboards in Tableau."),
    ("V05", "Orrin Health", "Operations Analyst", "US",
     "About the role: forecast nurse staffing with Python and Excel."),
    ("V06", "Pellow Freight", "Supply Chain Analyst", "US",
     "About the role: measure on-time delivery across 12 depots."),
    ("V07", "Pellow Freight", "Pricing Analyst", "US",
     "About the role: model lane prices. Sponsorship is not available for this role."),
    ("V08", "Saltmarsh Retail", "Merchandise Analyst", "US",
     "About the role: analyse our clearance sale markdowns and weekly sell-through."),
    ("V09", "Saltmarsh Retail", "Marketing Analyst", "US",
     "We proudly sponsor the city marathon every spring. "
     "About the role: measure campaign lift with SQL."),
    ("V10", "Tamsin Bank", "Risk Analyst", "US",
     "About the role: monitor credit risk models. We will not sponsor employment visas for this position."),
    ("V11", "Tamsin Bank", "Financial Analyst", "US",
     "About the role: build the branch profitability model."),
    ("V12", "Brindlecombe Aerospace", "Data Analyst", "US",
     "About the role: analyse test flight telemetry. This role requires U.S. citizenship because of ITAR export rules."),
    ("V13", "Brindlecombe Aerospace", "Business Analyst", "US",
     "About the role: support programme reporting. You must hold or be able to obtain a security clearance."),
    ("V14", "Quarry Lane Analytics", "Junior Data Analyst", "US",
     "About the role: clean client data in SQL. We sponsor H-1B visas and welcome OPT candidates."),
    ("V15", "Larchmere Insurance", "Claims Analyst", "US",
     "About the role: track claim cycle times. OPT candidates are welcome, but we do not sponsor H-1B visas."),
    ("V16", "Ashgrove Mutual", "Data Analyst", "GB",
     "About the role: build member retention reports in Power BI."),
    ("V17", "Ashgrove Mutual", "Pricing Analyst", "GB",
     "About the role: price home insurance. We can sponsor a Skilled Worker visa for this role."),
    ("V18", "Thistledown Media", "Audience Analyst", "GB",
     "About the role: report on podcast audiences each week."),
    ("V19", "Thistledown Media", "Commercial Analyst", "GB",
     "About the role: forecast ad revenue. We are unable to offer visa sponsorship."),
    ("V20", "Fenmoor Defence", "Data Analyst", "GB",
     "About the role: analyse maintenance logs. Applicants must hold active SC clearance."),
    ("V21", "Wrenfield Retail", "Trading Analyst", "GB",
     "About the role: weekly trading packs in Excel and SQL."),
    ("V22", "Cobbold & Hart", "Business Analyst", "GB",
     "About the role: support our audit analytics team."),
]

# employer name exactly as filed, fiscal year, state, new, continuing, denials
HISTORY = [
    ("KESTREL LEDGER INC", 2023, "WA", 4, 6, 0),
    ("KESTREL LEDGER INC", 2024, "WA", 5, 7, 1),
    ("KESTREL LEDGER, INC.", 2025, "WA", 3, 4, 0),
    ("KESTREL LEDGER INC FKA KESTREL BOOKS LLC", 2025, "WA", 2, 5, 0),
    ("ORRIN SERVICES CORP", 2024, "TX", 6, 9, 1),
    ("ORRIN SERVICES CORP", 2025, "TX", 7, 11, 0),
    ("ORRIN HEALTHCARE STAFFING INC", 2025, "FL", 40, 12, 3),
    ("PELLOW FREIGHT LLC", 2024, "OH", 0, 2, 0),
    ("PELLOW FREIGHT LLC", 2025, "OH", 0, 1, 0),
    ("SALTMARSH CONSULTING LLC", 2025, "NJ", 8, 3, 1),
    ("TAMSIN BANK NA", 2024, "NY", 20, 31, 2),
    ("TAMSIN BANK, NATIONAL ASSOCIATION", 2025, "NY", 18, 35, 1),
    ("BRINDLECOMBE AEROSPACE CORP", 2025, "CA", 3, 8, 0),
    ("HARROWGATE LABS LLC", 2024, "MA", 2, 1, 0),
    ("HARROWGATE LABS LLC", 2025, "MA", 1, 2, 0),
]

REGISTER = [
    ("ASHGROVE MUTUAL LIMITED", "Leeds", "Skilled Worker"),
    ("Thistledown Media Ltd", "Bristol", "Skilled Worker"),
    ("FENMOOR DEFENCE PLC", "Glasgow", "Skilled Worker"),
    ("COBBOLD AND HART LLP", "London", "Skilled Worker"),
    ("Wrenfield Holdings Ltd", "Norwich", "Skilled Worker"),
]

ALIASES = [
    ("Orrin Health", "ORRIN SERVICES CORP"),
]

# What a careful reader concludes for each committed posting, written out by hand.
TRUTH_SAYS = {
    "V01": "not_stated", "V02": "sponsors", "V03": "not_stated", "V04": "not_stated",
    "V05": "not_stated", "V06": "not_stated", "V07": "will_not_sponsor", "V08": "not_stated",
    "V09": "not_stated", "V10": "will_not_sponsor", "V11": "not_stated",
    "V12": "citizen_or_clearance", "V13": "citizen_or_clearance", "V14": "sponsors",
    "V15": "will_not_sponsor", "V16": "not_stated", "V17": "sponsors", "V18": "not_stated",
    "V19": "will_not_sponsor", "V20": "citizen_or_clearance", "V21": "not_stated", "V22": "not_stated",
}
# company -> the filed names that really belong to it (USCIS for US, register for GB)
TRUTH_NAMES = {
    "Kestrel Ledger": ["KESTREL LEDGER INC", "KESTREL LEDGER INC FKA KESTREL BOOKS LLC", "KESTREL LEDGER, INC."],
    "Orrin Health": ["ORRIN SERVICES CORP"],
    "Pellow Freight": ["PELLOW FREIGHT LLC"],
    "Saltmarsh Retail": [],
    "Tamsin Bank": ["TAMSIN BANK NA", "TAMSIN BANK, NATIONAL ASSOCIATION"],
    "Brindlecombe Aerospace": ["BRINDLECOMBE AEROSPACE CORP"],
    "Quarry Lane Analytics": [],
    "Larchmere Insurance": [],
    "Ashgrove Mutual": ["ASHGROVE MUTUAL LIMITED"],
    "Thistledown Media": ["Thistledown Media Ltd"],
    "Fenmoor Defence": ["FENMOOR DEFENCE PLC"],
    "Wrenfield Retail": [],
    "Cobbold & Hart": ["COBBOLD AND HART LLP"],
}

# Phrase banks for generated data.
SAYS_PHRASES = {
    "sponsors": [
        "H-1B sponsorship is available for this role.",
        "We sponsor H-1B visas for this team.",
        "Visa sponsorship is offered for the right candidate.",
        "We can sponsor a work visa for this position.",
    ],
    "will_not_sponsor": [
        "We will not sponsor employment visas for this position.",
        "Sponsorship is not available for this role.",
        "Candidates must be authorized to work without the need for sponsorship now or in the future.",
        "We are unable to offer visa sponsorship.",
        "OPT candidates are welcome, but we do not sponsor H-1B visas.",
        "This company can't sponsor visas at this time.",
    ],
    "citizen_or_clearance": [
        "This role requires U.S. citizenship because of ITAR export rules.",
        "You must hold or be able to obtain a security clearance.",
        "Applicants must hold active SC clearance.",
        "Only U.S. persons may apply, as defined by export control law.",
    ],
    "not_stated": [""],
}
DECOYS = [
    "",
    "We proudly sponsor the city marathon every spring.",
    "You will analyse our clearance sale markdowns.",
    "Candidates must be authorized to work in the U.S.",
    "Our sponsorship team manages event partners.",
]
STEMS = ["Alderwick", "Bramblecote", "Corriemoor", "Dunlavin", "Elsworth", "Foxcombe", "Gorsefield",
         "Hartwell Vale", "Ivybridge Row", "Kilnsey", "Lowther Park", "Merrowby", "Netherby Cross",
         "Oakhanger", "Pennycross", "Rookwith"]
SECTORS = ["Analytics", "Freight", "Health", "Bank", "Retail", "Media", "Insurance", "Foods"]
US_SUFFIXES = ["INC", "INC.", "LLC", "CORP", "CORPORATION"]
GB_SUFFIXES = ["LIMITED", "LTD", "PLC", "LLP"]
TITLES = ["Data Analyst", "Business Analyst", "Product Analyst", "Financial Analyst", "Operations Analyst"]


def _filed(rng, company, country):
    """One way an employer's name might be filed: upper case, odd punctuation, a legal suffix."""
    name = company.upper()
    if rng.random() < 0.4:
        name = name.replace(" ", ", ", 1) if " " in name else name
    suffix = rng.choice(US_SUFFIXES if country == "US" else GB_SUFFIXES)
    if rng.random() < 0.5:
        suffix = suffix + "."
    return name + ", " + suffix if rng.random() < 0.5 else name + " " + suffix


def build(seed=SEED):
    """{"postings", "history", "register", "aliases": rows as lists, "truth": {"says", "names"}}."""
    if seed == SEED:
        return {
            "postings": [list(p) for p in POSTINGS],
            "history": [list(h) for h in HISTORY],
            "register": [list(r) for r in REGISTER],
            "aliases": [list(a) for a in ALIASES],
            "truth": {"says": dict(TRUTH_SAYS), "names": {k: sorted(v) for k, v in TRUTH_NAMES.items()}},
        }
    rng = random.Random(seed)
    stems = rng.sample(STEMS, 10)
    postings, history, register, aliases = [], [], [], []
    says, names = {}, {}
    n = 0
    for stem in stems:
        company = stem + " " + rng.choice(SECTORS)
        country = rng.choice(["US", "US", "GB"])
        kind = rng.choice(["none", "plain", "variants", "alias"])
        mine = []
        if kind == "plain":
            mine = [_filed(rng, company, country)]
        elif kind == "variants":
            first = _filed(rng, company, country)
            mine = [first, _filed(rng, company, country),
                    first + " FKA " + stem.upper() + " HOLDINGS " + rng.choice(US_SUFFIXES)]
        elif kind == "alias":
            other = stem.upper() + " SERVICES " + rng.choice(US_SUFFIXES if country == "US" else GB_SUFFIXES)
            mine = [other]
            aliases.append([company, other])
        mine = sorted(set(mine))
        names[company] = mine
        for name in mine:
            if country == "US":
                for fy in rng.sample([2023, 2024, 2025], rng.randint(1, 3)):
                    history.append([name, fy, rng.choice(["WA", "NY", "TX", "CA"]),
                                    rng.randint(0, 30), rng.randint(0, 40), rng.randint(0, 3)])
            else:
                register.append([name, rng.choice(["Leeds", "Bristol", "London", "Cardiff"]), "Skilled Worker"])
        if rng.random() < 0.5:
            decoy = company.upper() + " STAFFING " + rng.choice(US_SUFFIXES if country == "US" else GB_SUFFIXES)
            if country == "US":
                history.append([decoy, 2025, "FL", rng.randint(1, 50), rng.randint(0, 20), 0])
            else:
                register.append([decoy, "Leeds", "Skilled Worker"])
        for _ in range(rng.randint(1, 3)):
            n += 1
            pid = "V%02d" % n
            label = rng.choice(["sponsors", "will_not_sponsor", "citizen_or_clearance",
                                "not_stated", "not_stated", "not_stated"])
            body = "About the role: report on weekly %s metrics." % rng.choice(["sales", "risk", "usage", "cost"])
            parts = [rng.choice(DECOYS) if label == "not_stated" else "", body,
                     rng.choice(SAYS_PHRASES[label])]
            text = " ".join(p for p in parts if p)
            postings.append([pid, company, rng.choice(TITLES), country, text])
            says[pid] = label
    history.sort(key=lambda r: (r[0], r[1]))
    register.sort()
    return {"postings": postings, "history": history, "register": register, "aliases": aliases,
            "truth": {"says": says, "names": names}}


def write_csv(path, header, rows):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def main():
    data = build()
    d = os.path.join(HERE, "data")
    os.makedirs(d, exist_ok=True)
    write_csv(os.path.join(d, "postings.csv"), ["posting_id", "company", "title", "country", "text"], data["postings"])
    write_csv(os.path.join(d, "uscis_history.csv"),
              ["employer_name", "fiscal_year", "state", "new_approvals", "continuing_approvals", "denials"],
              data["history"])
    write_csv(os.path.join(d, "uk_register.csv"), ["organisation_name", "town", "route"], data["register"])
    write_csv(os.path.join(d, "aliases.csv"), ["company", "filed_name"], data["aliases"])
    print("wrote %d postings, %d history rows, %d register rows, %d aliases"
          % (len(data["postings"]), len(data["history"]), len(data["register"]), len(data["aliases"])))


if __name__ == "__main__":
    main()
